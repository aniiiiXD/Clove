#include "kernel/llm_client.hpp"
#include <spdlog/spdlog.h>
#include <nlohmann/json.hpp>

#include <cstdlib>
#include <unistd.h>
#include <signal.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <filesystem>
#include <fstream>

using json = nlohmann::json;

namespace agentos::kernel {

// Load environment variables from .env file
static void load_dotenv() {
    static bool loaded = false;
    if (loaded) return;
    loaded = true;

    // Search for .env in multiple locations
    std::vector<std::filesystem::path> search_paths = {
        std::filesystem::current_path() / ".env",
        "../.env",
        "../../.env",
    };

    // Also check relative to executable
    char exe_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len != -1) {
        exe_path[len] = '\0';
        auto exe_dir = std::filesystem::path(exe_path).parent_path();
        search_paths.push_back(exe_dir / ".env");
        search_paths.push_back(exe_dir / "../.env");
        search_paths.push_back(exe_dir.parent_path() / ".env");
    }

    for (const auto& env_path : search_paths) {
        if (std::filesystem::exists(env_path)) {
            std::ifstream file(env_path);
            std::string line;
            while (std::getline(file, line)) {
                // Trim whitespace
                size_t start = line.find_first_not_of(" \t\r\n");
                if (start == std::string::npos) continue;
                line = line.substr(start);

                // Skip comments
                if (line.empty() || line[0] == '#') continue;

                // Find = separator
                size_t eq_pos = line.find('=');
                if (eq_pos == std::string::npos) continue;

                std::string key = line.substr(0, eq_pos);
                std::string value = line.substr(eq_pos + 1);

                // Trim key
                size_t key_end = key.find_last_not_of(" \t");
                if (key_end != std::string::npos) key = key.substr(0, key_end + 1);

                // Trim value and remove quotes
                start = value.find_first_not_of(" \t");
                if (start != std::string::npos) value = value.substr(start);
                size_t val_end = value.find_last_not_of(" \t\r\n");
                if (val_end != std::string::npos) value = value.substr(0, val_end + 1);

                // Remove surrounding quotes
                if (value.size() >= 2) {
                    if ((value.front() == '"' && value.back() == '"') ||
                        (value.front() == '\'' && value.back() == '\'')) {
                        value = value.substr(1, value.size() - 2);
                    }
                }

                // Only set if not already in environment
                if (!key.empty() && !value.empty() && std::getenv(key.c_str()) == nullptr) {
                    setenv(key.c_str(), value.c_str(), 0);
                }
            }
            spdlog::debug("Loaded environment from {}", env_path.string());
            break;
        }
    }
}

LLMClient::LLMClient(const LLMConfig& config)
    : config_(config) {
    // Load .env file first
    load_dotenv();

    if (config_.api_key.empty()) {
        config_.api_key = get_api_key_from_env();
    }

    // Check environment variable for model name
    std::string env_model = get_model_from_env();
    if (!env_model.empty()) {
        config_.model = env_model;
    }

    if (config_.api_key.empty()) {
        spdlog::warn("No Gemini API key configured. Set GEMINI_API_KEY in environment or .env file.");
    } else {
        spdlog::info("LLM client initialized (model={})", config_.model);
    }
}

LLMClient::~LLMClient() {
    stop_subprocess();
}

bool LLMClient::is_configured() const {
    return !config_.api_key.empty();
}

std::string LLMClient::get_api_key_from_env() {
    const char* key = std::getenv("GEMINI_API_KEY");
    if (key) {
        return std::string(key);
    }

    // Also check GOOGLE_API_KEY as fallback
    key = std::getenv("GOOGLE_API_KEY");
    if (key) {
        return std::string(key);
    }

    return "";
}

std::string LLMClient::get_model_from_env() {
    const char* model = std::getenv("GEMINI_MODEL");
    if (model) {
        return std::string(model);
    }
    return "";
}

bool LLMClient::start_subprocess() {
    if (subprocess_started_) {
        return true;
    }

    // Find the llm_service.py script
    // Look in several locations relative to the executable
    std::vector<std::string> search_paths = {
        "agents/llm_service/llm_service.py",
        "../agents/llm_service/llm_service.py",
        "../../agents/llm_service/llm_service.py",
    };

    // Also check relative to executable path
    char exe_path[PATH_MAX];
    ssize_t len = readlink("/proc/self/exe", exe_path, sizeof(exe_path) - 1);
    if (len != -1) {
        exe_path[len] = '\0';
        std::filesystem::path exe_dir = std::filesystem::path(exe_path).parent_path();
        search_paths.push_back((exe_dir / "agents/llm_service/llm_service.py").string());
        search_paths.push_back((exe_dir / "../agents/llm_service/llm_service.py").string());
        search_paths.push_back((exe_dir.parent_path() / "agents/llm_service/llm_service.py").string());
    }

    std::string script_path;
    for (const auto& path : search_paths) {
        if (std::filesystem::exists(path)) {
            script_path = std::filesystem::canonical(path).string();
            break;
        }
    }

    if (script_path.empty()) {
        spdlog::error("Could not find llm_service.py");
        return false;
    }

    spdlog::debug("Starting LLM subprocess: python3 {}", script_path);

    // Create pipes for stdin and stdout
    int stdin_pipe[2];
    int stdout_pipe[2];

    if (pipe(stdin_pipe) == -1 || pipe(stdout_pipe) == -1) {
        spdlog::error("Failed to create pipes for subprocess");
        return false;
    }

    pid_t pid = fork();
    if (pid == -1) {
        spdlog::error("Failed to fork subprocess");
        close(stdin_pipe[0]);
        close(stdin_pipe[1]);
        close(stdout_pipe[0]);
        close(stdout_pipe[1]);
        return false;
    }

    if (pid == 0) {
        // Child process
        // Redirect stdin
        close(stdin_pipe[1]);  // Close write end
        dup2(stdin_pipe[0], STDIN_FILENO);
        close(stdin_pipe[0]);

        // Redirect stdout
        close(stdout_pipe[0]);  // Close read end
        dup2(stdout_pipe[1], STDOUT_FILENO);
        close(stdout_pipe[1]);

        // Execute Python script
        execlp("python3", "python3", script_path.c_str(), nullptr);

        // If exec fails
        _exit(127);
    }

    // Parent process
    close(stdin_pipe[0]);   // Close read end of stdin pipe
    close(stdout_pipe[1]);  // Close write end of stdout pipe

    subprocess_stdin_ = fdopen(stdin_pipe[1], "w");
    subprocess_stdout_ = fdopen(stdout_pipe[0], "r");
    subprocess_pid_ = pid;

    if (!subprocess_stdin_ || !subprocess_stdout_) {
        spdlog::error("Failed to create file handles for subprocess");
        stop_subprocess();
        return false;
    }

    // Set stdout to non-blocking for timeout handling
    int flags = fcntl(fileno(subprocess_stdout_), F_GETFL, 0);
    // Keep blocking for now, handle timeout differently if needed

    subprocess_started_ = true;
    spdlog::info("LLM subprocess started (pid={})", subprocess_pid_);
    return true;
}

void LLMClient::stop_subprocess() {
    if (subprocess_stdin_) {
        fclose(subprocess_stdin_);
        subprocess_stdin_ = nullptr;
    }

    if (subprocess_stdout_) {
        fclose(subprocess_stdout_);
        subprocess_stdout_ = nullptr;
    }

    if (subprocess_pid_ > 0) {
        // Send SIGTERM and wait
        kill(subprocess_pid_, SIGTERM);
        int status;
        waitpid(subprocess_pid_, &status, 0);
        spdlog::debug("LLM subprocess terminated (pid={})", subprocess_pid_);
        subprocess_pid_ = -1;
    }

    subprocess_started_ = false;
}

LLMResponse LLMClient::call_subprocess(const std::string& request_json) {
    LLMResponse response;

    if (!subprocess_started_ && !start_subprocess()) {
        response.success = false;
        response.error = "Failed to start LLM subprocess";
        return response;
    }

    // Write request to subprocess stdin (one line)
    std::string request_line = request_json + "\n";
    if (fputs(request_line.c_str(), subprocess_stdin_) == EOF) {
        response.success = false;
        response.error = "Failed to write to subprocess";
        stop_subprocess();
        return response;
    }
    fflush(subprocess_stdin_);

    // Read response from subprocess stdout (one line)
    char buffer[65536];
    if (fgets(buffer, sizeof(buffer), subprocess_stdout_) == nullptr) {
        response.success = false;
        response.error = "Failed to read from subprocess";
        stop_subprocess();
        return response;
    }

    return parse_subprocess_response(buffer);
}

LLMResponse LLMClient::parse_subprocess_response(const std::string& response_json) {
    LLMResponse response;

    try {
        json j = json::parse(response_json);

        response.success = j.value("success", false);
        response.content = j.value("content", "");
        response.error = j.value("error", "");
        response.tokens_used = j.value("tokens", 0);

    } catch (const std::exception& e) {
        response.success = false;
        response.error = std::string("JSON parse error: ") + e.what();
        spdlog::error("Failed to parse subprocess response: {}", e.what());
    }

    return response;
}

std::string LLMClient::build_simple_request_json(const std::string& prompt) {
    json request;
    request["prompt"] = prompt;
    request["model"] = config_.model;
    request["temperature"] = config_.temperature;
    request["max_tokens"] = config_.max_tokens;
    return request.dump();
}

std::string LLMClient::build_chat_request_json(const std::vector<ChatMessage>& messages) {
    // For chat, concatenate messages into a single prompt
    // The Python service handles the actual conversation format
    std::string combined_prompt;
    for (const auto& msg : messages) {
        if (!combined_prompt.empty()) {
            combined_prompt += "\n\n";
        }
        if (msg.role == "user") {
            combined_prompt += "User: " + msg.content;
        } else {
            combined_prompt += "Assistant: " + msg.content;
        }
    }

    return build_simple_request_json(combined_prompt);
}

LLMResponse LLMClient::complete(const std::string& prompt) {
    if (!is_configured()) {
        LLMResponse response;
        response.success = false;
        response.error = "API key not configured";
        return response;
    }

    std::string request_json = build_simple_request_json(prompt);
    return call_subprocess(request_json);
}

LLMResponse LLMClient::chat(const std::vector<ChatMessage>& messages) {
    if (!is_configured()) {
        LLMResponse response;
        response.success = false;
        response.error = "API key not configured";
        return response;
    }

    std::string request_json = build_chat_request_json(messages);
    return call_subprocess(request_json);
}

LLMResponse LLMClient::complete_with_options(const std::string& json_payload) {
    if (!is_configured()) {
        LLMResponse response;
        response.success = false;
        response.error = "API key not configured";
        return response;
    }

    // Parse the incoming JSON to add default config values if not present
    try {
        json request = json::parse(json_payload);

        // Add defaults from config if not specified
        if (!request.contains("model")) {
            request["model"] = config_.model;
        }
        if (!request.contains("temperature")) {
            request["temperature"] = config_.temperature;
        }
        if (!request.contains("max_tokens")) {
            request["max_tokens"] = config_.max_tokens;
        }

        return call_subprocess(request.dump());

    } catch (const std::exception& e) {
        // If JSON parsing fails, treat as plain text prompt
        spdlog::debug("Payload not JSON, treating as plain prompt");
        return complete(json_payload);
    }
}

} // namespace agentos::kernel
