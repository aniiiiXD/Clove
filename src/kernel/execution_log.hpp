/**
 * Clove Execution Log
 *
 * Records syscall execution for deterministic replay and debugging.
 * Supports recording, checkpointing, and playback of agent activities.
 */
#pragma once
#include <string>
#include <vector>
#include <deque>
#include <mutex>
#include <chrono>
#include <cstdint>
#include <nlohmann/json.hpp>

namespace agentos::kernel {

// Execution log entry for recording syscalls
struct ExecutionLogEntry {
    uint64_t sequence_id;                       // Monotonic sequence number
    std::chrono::system_clock::time_point timestamp;
    uint32_t agent_id;                          // Agent that made the call
    uint8_t opcode;                             // Syscall opcode
    std::string payload;                        // Request payload (JSON)
    std::string response;                       // Response payload (JSON)
    uint64_t duration_us;                       // Execution duration in microseconds
    bool success;                               // Whether syscall succeeded

    // Convert to JSON
    nlohmann::json to_json() const;

    // Create from JSON
    static ExecutionLogEntry from_json(const nlohmann::json& j);
};

// Recording session state
enum class RecordingState {
    IDLE,       // Not recording
    RECORDING,  // Actively recording
    PAUSED      // Recording paused
};

// Recording configuration
struct RecordingConfig {
    size_t max_entries = 50000;             // Max entries in buffer
    bool include_think = false;             // Include LLM calls (non-deterministic)
    bool include_http = false;              // Include HTTP calls (non-deterministic)
    bool include_exec = false;              // Include exec calls (may be non-deterministic)
    std::vector<uint32_t> filter_agents;    // Only record these agents (empty = all)
};

// Replay session state
enum class ReplayState {
    IDLE,       // Not replaying
    RUNNING,    // Actively replaying
    PAUSED,     // Replay paused
    COMPLETED,  // Replay finished
    ERROR       // Replay encountered error
};

// Replay progress info
struct ReplayProgress {
    ReplayState state = ReplayState::IDLE;
    uint64_t total_entries = 0;
    uint64_t current_entry = 0;
    uint64_t entries_replayed = 0;
    uint64_t entries_skipped = 0;
    std::string last_error;
};

// Execution logger class
class ExecutionLogger {
public:
    ExecutionLogger();
    explicit ExecutionLogger(const RecordingConfig& config);
    ~ExecutionLogger() = default;

    // Recording control
    bool start_recording();
    bool stop_recording();
    bool pause_recording();
    bool resume_recording();
    RecordingState recording_state() const { return recording_state_; }

    // Log a syscall execution
    void log_syscall(uint32_t agent_id, uint8_t opcode,
                     const std::string& payload, const std::string& response,
                     uint64_t duration_us, bool success);

    // Query methods
    std::vector<ExecutionLogEntry> get_entries(
        uint64_t start_sequence = 0,
        size_t limit = 100
    ) const;

    std::vector<ExecutionLogEntry> get_entries_for_agent(
        uint32_t agent_id,
        size_t limit = 100
    ) const;

    // Export recorded session
    std::string export_recording() const;   // Returns JSON array

    // Import recording for replay
    bool import_recording(const std::string& json_data);

    // Replay control
    bool start_replay();
    bool stop_replay();
    bool pause_replay();
    bool resume_replay();
    ReplayProgress get_replay_progress() const;

    // Get next entry for replay
    const ExecutionLogEntry* get_next_replay_entry();

    // Mark current entry as replayed
    void advance_replay(bool skipped = false);

    // Configuration
    void set_config(const RecordingConfig& config);
    const RecordingConfig& get_config() const { return config_; }

    // Clear all entries
    void clear();

    // Get statistics
    size_t entry_count() const;
    uint64_t last_sequence_id() const;

private:
    RecordingConfig config_;
    std::deque<ExecutionLogEntry> entries_;
    mutable std::mutex mutex_;

    // Recording state
    RecordingState recording_state_ = RecordingState::IDLE;
    uint64_t next_sequence_id_ = 1;

    // Replay state
    std::vector<ExecutionLogEntry> replay_entries_;  // Imported entries
    ReplayState replay_state_ = ReplayState::IDLE;
    size_t replay_index_ = 0;
    uint64_t entries_replayed_ = 0;
    uint64_t entries_skipped_ = 0;
    std::string replay_error_;

    // Trim entries to max size
    void trim_entries();

    // Check if syscall should be recorded
    bool should_record(uint8_t opcode) const;
};

} // namespace agentos::kernel
