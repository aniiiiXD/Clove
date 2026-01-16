#pragma once
#include <string>
#include <vector>
#include <optional>
#include <functional>
#include <memory>
#include <cstdio>
#include <sys/types.h>

namespace agentos::kernel {

// LLM configuration
struct LLMConfig {
    std::string api_key;                                    // Gemini API key
    std::string model = "gemini-2.0-flash";                 // Model to use
    std::string api_host = "generativelanguage.googleapis.com";
    int timeout_seconds = 30;
    float temperature = 0.7f;
    int max_tokens = 1024;
};

// Chat message
struct ChatMessage {
    std::string role;    // "user" or "model"
    std::string content;
};

// LLM response
struct LLMResponse {
    bool success = false;
    std::string content;
    std::string error;
    int tokens_used = 0;
};

// Callback for streaming responses (future use)
using StreamCallback = std::function<void(const std::string& chunk)>;

class LLMClient {
public:
    explicit LLMClient(const LLMConfig& config);
    ~LLMClient();

    // Non-copyable
    LLMClient(const LLMClient&) = delete;
    LLMClient& operator=(const LLMClient&) = delete;

    // Check if configured (has API key)
    bool is_configured() const;

    // Simple completion
    LLMResponse complete(const std::string& prompt);

    // Chat completion with history
    LLMResponse chat(const std::vector<ChatMessage>& messages);

    // Get/set config
    const LLMConfig& config() const { return config_; }
    void set_api_key(const std::string& key) { config_.api_key = key; }
    void set_model(const std::string& model) { config_.model = model; }

    // Load API key from environment
    static std::string get_api_key_from_env();

    // Load model name from environment
    static std::string get_model_from_env();

    // Complete with extended options (JSON payload)
    LLMResponse complete_with_options(const std::string& json_payload);

private:
    LLMConfig config_;

    // Subprocess management
    FILE* subprocess_stdin_ = nullptr;
    FILE* subprocess_stdout_ = nullptr;
    pid_t subprocess_pid_ = -1;
    bool subprocess_started_ = false;

    // Start the Python LLM subprocess
    bool start_subprocess();

    // Stop the Python LLM subprocess
    void stop_subprocess();

    // Call the subprocess with a JSON request
    LLMResponse call_subprocess(const std::string& request_json);

    // Build request JSON for simple prompt
    std::string build_simple_request_json(const std::string& prompt);

    // Build request JSON for chat messages
    std::string build_chat_request_json(const std::vector<ChatMessage>& messages);

    // Parse JSON response from subprocess
    LLMResponse parse_subprocess_response(const std::string& response_json);
};

} // namespace agentos::kernel
