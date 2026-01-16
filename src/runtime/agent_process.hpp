#pragma once
#include <string>
#include <memory>
#include <vector>
#include <functional>
#include <cstdint>
#include "runtime/sandbox.hpp"

namespace agentos::runtime {

// Agent configuration
struct AgentConfig {
    std::string name;
    std::string script_path;               // Path to Python script
    std::string python_path = "python3";   // Python interpreter
    std::string socket_path;               // Kernel socket to connect to

    // Resource limits
    ResourceLimits limits;

    // Sandbox options
    bool sandboxed = true;
    bool enable_network = false;
};

// Agent state
enum class AgentState {
    CREATED,
    STARTING,
    RUNNING,
    STOPPING,
    STOPPED,
    FAILED
};

const char* agent_state_to_string(AgentState state);

// Agent metrics snapshot
struct AgentMetrics {
    uint32_t id;
    std::string name;
    pid_t pid;
    AgentState state;

    // Resource usage (populated from cgroups)
    uint64_t memory_bytes;
    double cpu_percent;
    uint64_t uptime_seconds;

    // LLM activity
    uint64_t llm_request_count;
    uint64_t llm_tokens_used;

    // Hierarchy
    uint32_t parent_id;  // 0 = kernel-spawned
    std::vector<uint32_t> child_ids;

    // Timestamps
    uint64_t created_at_ms;
};

// Forward declaration
class AgentProcess;

// Callback for agent events
using AgentEventCallback = std::function<void(AgentProcess*, AgentState)>;

class AgentProcess {
public:
    explicit AgentProcess(const AgentConfig& config);
    ~AgentProcess();

    // Non-copyable
    AgentProcess(const AgentProcess&) = delete;
    AgentProcess& operator=(const AgentProcess&) = delete;

    // Lifecycle
    bool start();
    bool stop(int timeout_ms = 5000);
    bool restart();

    // Status
    AgentState state() const { return state_; }
    const std::string& name() const { return config_.name; }
    uint32_t id() const { return id_; }
    pid_t pid() const;

    // Wait for agent to exit
    int wait();

    // Check if running
    bool is_running() const;

    // Get exit code
    int exit_code() const { return exit_code_; }

    // Event callback
    void set_event_callback(AgentEventCallback callback);

    // Metrics
    AgentMetrics get_metrics() const;
    void record_llm_call(int tokens);

    // Hierarchy
    void set_parent_id(uint32_t parent_id) { parent_id_ = parent_id; }
    uint32_t parent_id() const { return parent_id_; }
    void add_child(uint32_t child_id);
    const std::vector<uint32_t>& child_ids() const { return child_ids_; }

    // Static: generate unique ID
    static uint32_t generate_id();

private:
    AgentConfig config_;
    AgentState state_ = AgentState::CREATED;
    uint32_t id_;
    int exit_code_ = -1;

    std::unique_ptr<Sandbox> sandbox_;
    AgentEventCallback event_callback_;

    // Metrics tracking
    uint64_t llm_request_count_ = 0;
    uint64_t llm_tokens_used_ = 0;
    uint32_t parent_id_ = 0;
    std::vector<uint32_t> child_ids_;
    uint64_t created_at_ms_ = 0;

    void set_state(AgentState new_state);
    std::vector<std::string> build_args() const;
};

// Agent manager - handles multiple agents
class AgentManager {
public:
    AgentManager(const std::string& kernel_socket);
    ~AgentManager();

    // Create and start an agent
    std::shared_ptr<AgentProcess> spawn_agent(const AgentConfig& config);

    // Get agent by name or ID
    std::shared_ptr<AgentProcess> get_agent(const std::string& name);
    std::shared_ptr<AgentProcess> get_agent(uint32_t id);

    // Stop and remove agent
    bool kill_agent(const std::string& name);
    bool kill_agent(uint32_t id);

    // List agents
    std::vector<std::shared_ptr<AgentProcess>> list_agents() const;

    // Stop all agents
    void stop_all();

    // Check for dead agents and clean up
    void reap_agents();

private:
    std::string kernel_socket_;
    std::unordered_map<std::string, std::shared_ptr<AgentProcess>> agents_by_name_;
    std::unordered_map<uint32_t, std::shared_ptr<AgentProcess>> agents_by_id_;
    SandboxManager sandbox_manager_;
};

} // namespace agentos::runtime
