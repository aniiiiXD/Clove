#include "kernel/execution_log.hpp"
#include "ipc/protocol.hpp"
#include <spdlog/spdlog.h>
#include <iomanip>
#include <sstream>

namespace agentos::kernel {

using json = nlohmann::json;

// ============================================================================
// ExecutionLogEntry Implementation
// ============================================================================

json ExecutionLogEntry::to_json() const {
    json j;
    j["sequence_id"] = sequence_id;

    // Format timestamp as ISO 8601
    auto time_t = std::chrono::system_clock::to_time_t(timestamp);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        timestamp.time_since_epoch()) % 1000;
    std::ostringstream oss;
    oss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S");
    oss << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';
    j["timestamp"] = oss.str();

    j["agent_id"] = agent_id;
    j["opcode"] = opcode;
    j["opcode_name"] = ipc::opcode_to_string(static_cast<ipc::SyscallOp>(opcode));
    j["payload"] = payload;
    j["response"] = response;
    j["duration_us"] = duration_us;
    j["success"] = success;

    return j;
}

ExecutionLogEntry ExecutionLogEntry::from_json(const json& j) {
    ExecutionLogEntry entry;
    entry.sequence_id = j.value("sequence_id", 0ULL);
    entry.agent_id = j.value("agent_id", 0U);
    entry.opcode = j.value("opcode", 0);
    entry.payload = j.value("payload", "");
    entry.response = j.value("response", "");
    entry.duration_us = j.value("duration_us", 0ULL);
    entry.success = j.value("success", true);

    // Parse timestamp if present
    std::string ts = j.value("timestamp", "");
    if (!ts.empty()) {
        // Parse ISO 8601 timestamp
        std::tm tm = {};
        int ms = 0;
        if (sscanf(ts.c_str(), "%d-%d-%dT%d:%d:%d.%dZ",
                   &tm.tm_year, &tm.tm_mon, &tm.tm_mday,
                   &tm.tm_hour, &tm.tm_min, &tm.tm_sec, &ms) >= 6) {
            tm.tm_year -= 1900;
            tm.tm_mon -= 1;
            auto tp = std::chrono::system_clock::from_time_t(timegm(&tm));
            tp += std::chrono::milliseconds(ms);
            entry.timestamp = tp;
        } else {
            entry.timestamp = std::chrono::system_clock::now();
        }
    } else {
        entry.timestamp = std::chrono::system_clock::now();
    }

    return entry;
}

// ============================================================================
// ExecutionLogger Implementation
// ============================================================================

ExecutionLogger::ExecutionLogger() : config_() {
    spdlog::debug("ExecutionLogger initialized with default config");
}

ExecutionLogger::ExecutionLogger(const RecordingConfig& config) : config_(config) {
    spdlog::debug("ExecutionLogger initialized (max_entries={})", config_.max_entries);
}

bool ExecutionLogger::start_recording() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (recording_state_ == RecordingState::RECORDING) {
        spdlog::warn("Recording already in progress");
        return false;
    }

    // Clear previous entries if starting fresh
    if (recording_state_ == RecordingState::IDLE) {
        entries_.clear();
        next_sequence_id_ = 1;
    }

    recording_state_ = RecordingState::RECORDING;
    spdlog::info("Execution recording started");
    return true;
}

bool ExecutionLogger::stop_recording() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (recording_state_ == RecordingState::IDLE) {
        spdlog::warn("No recording in progress");
        return false;
    }

    recording_state_ = RecordingState::IDLE;
    spdlog::info("Execution recording stopped ({} entries)", entries_.size());
    return true;
}

bool ExecutionLogger::pause_recording() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (recording_state_ != RecordingState::RECORDING) {
        spdlog::warn("Recording not active");
        return false;
    }

    recording_state_ = RecordingState::PAUSED;
    spdlog::debug("Execution recording paused");
    return true;
}

bool ExecutionLogger::resume_recording() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (recording_state_ != RecordingState::PAUSED) {
        spdlog::warn("Recording not paused");
        return false;
    }

    recording_state_ = RecordingState::RECORDING;
    spdlog::debug("Execution recording resumed");
    return true;
}

bool ExecutionLogger::should_record(uint8_t opcode) const {
    // Check if syscall type should be recorded
    auto op = static_cast<ipc::SyscallOp>(opcode);

    // Skip non-deterministic syscalls unless explicitly included
    if (op == ipc::SyscallOp::SYS_THINK && !config_.include_think) {
        return false;
    }
    if (op == ipc::SyscallOp::SYS_HTTP && !config_.include_http) {
        return false;
    }
    if (op == ipc::SyscallOp::SYS_EXEC && !config_.include_exec) {
        return false;
    }

    // Skip read-only syscalls that don't affect state
    if (op == ipc::SyscallOp::SYS_LIST ||
        op == ipc::SyscallOp::SYS_GET_PERMS ||
        op == ipc::SyscallOp::SYS_KEYS ||
        op == ipc::SyscallOp::SYS_POLL_EVENTS ||
        op == ipc::SyscallOp::SYS_METRICS_SYSTEM ||
        op == ipc::SyscallOp::SYS_METRICS_AGENT ||
        op == ipc::SyscallOp::SYS_METRICS_ALL_AGENTS ||
        op == ipc::SyscallOp::SYS_METRICS_CGROUP ||
        op == ipc::SyscallOp::SYS_GET_AUDIT_LOG ||
        op == ipc::SyscallOp::SYS_TUNNEL_STATUS ||
        op == ipc::SyscallOp::SYS_TUNNEL_LIST_REMOTES ||
        op == ipc::SyscallOp::SYS_WORLD_LIST ||
        op == ipc::SyscallOp::SYS_WORLD_STATE) {
        return false;
    }

    return true;
}

void ExecutionLogger::log_syscall(uint32_t agent_id, uint8_t opcode,
                                  const std::string& payload,
                                  const std::string& response,
                                  uint64_t duration_us, bool success) {
    std::lock_guard<std::mutex> lock(mutex_);

    // Check if we're recording
    if (recording_state_ != RecordingState::RECORDING) {
        return;
    }

    // Check if this syscall should be recorded
    if (!should_record(opcode)) {
        return;
    }

    // Check agent filter
    if (!config_.filter_agents.empty()) {
        bool found = false;
        for (uint32_t id : config_.filter_agents) {
            if (id == agent_id) {
                found = true;
                break;
            }
        }
        if (!found) {
            return;
        }
    }

    ExecutionLogEntry entry;
    entry.sequence_id = next_sequence_id_++;
    entry.timestamp = std::chrono::system_clock::now();
    entry.agent_id = agent_id;
    entry.opcode = opcode;
    entry.payload = payload;
    entry.response = response;
    entry.duration_us = duration_us;
    entry.success = success;

    entries_.push_back(entry);
    trim_entries();

    spdlog::trace("Recorded syscall: seq={} agent={} opcode={}",
                  entry.sequence_id, agent_id, ipc::opcode_to_string(static_cast<ipc::SyscallOp>(opcode)));
}

std::vector<ExecutionLogEntry> ExecutionLogger::get_entries(
    uint64_t start_sequence, size_t limit) const {

    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<ExecutionLogEntry> result;

    for (const auto& entry : entries_) {
        if (entry.sequence_id > start_sequence) {
            result.push_back(entry);
            if (result.size() >= limit) {
                break;
            }
        }
    }

    return result;
}

std::vector<ExecutionLogEntry> ExecutionLogger::get_entries_for_agent(
    uint32_t agent_id, size_t limit) const {

    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<ExecutionLogEntry> result;

    for (auto it = entries_.rbegin(); it != entries_.rend() && result.size() < limit; ++it) {
        if (it->agent_id == agent_id) {
            result.push_back(*it);
        }
    }

    std::reverse(result.begin(), result.end());
    return result;
}

std::string ExecutionLogger::export_recording() const {
    std::lock_guard<std::mutex> lock(mutex_);

    json arr = json::array();
    for (const auto& entry : entries_) {
        arr.push_back(entry.to_json());
    }

    return arr.dump();
}

bool ExecutionLogger::import_recording(const std::string& json_data) {
    std::lock_guard<std::mutex> lock(mutex_);

    try {
        json arr = json::parse(json_data);
        if (!arr.is_array()) {
            spdlog::error("Recording data must be a JSON array");
            return false;
        }

        replay_entries_.clear();
        for (const auto& j : arr) {
            replay_entries_.push_back(ExecutionLogEntry::from_json(j));
        }

        spdlog::info("Imported {} entries for replay", replay_entries_.size());
        return true;

    } catch (const std::exception& e) {
        spdlog::error("Failed to parse recording data: {}", e.what());
        return false;
    }
}

bool ExecutionLogger::start_replay() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (replay_entries_.empty()) {
        replay_error_ = "No recording loaded";
        replay_state_ = ReplayState::ERROR;
        return false;
    }

    if (replay_state_ == ReplayState::RUNNING) {
        replay_error_ = "Replay already in progress";
        return false;
    }

    replay_state_ = ReplayState::RUNNING;
    replay_index_ = 0;
    entries_replayed_ = 0;
    entries_skipped_ = 0;
    replay_error_.clear();

    spdlog::info("Replay started ({} entries)", replay_entries_.size());
    return true;
}

bool ExecutionLogger::stop_replay() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (replay_state_ == ReplayState::IDLE) {
        return false;
    }

    replay_state_ = ReplayState::IDLE;
    spdlog::info("Replay stopped (replayed={}, skipped={})",
                 entries_replayed_, entries_skipped_);
    return true;
}

bool ExecutionLogger::pause_replay() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (replay_state_ != ReplayState::RUNNING) {
        return false;
    }

    replay_state_ = ReplayState::PAUSED;
    spdlog::debug("Replay paused at entry {}", replay_index_);
    return true;
}

bool ExecutionLogger::resume_replay() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (replay_state_ != ReplayState::PAUSED) {
        return false;
    }

    replay_state_ = ReplayState::RUNNING;
    spdlog::debug("Replay resumed at entry {}", replay_index_);
    return true;
}

ReplayProgress ExecutionLogger::get_replay_progress() const {
    std::lock_guard<std::mutex> lock(mutex_);

    ReplayProgress progress;
    progress.state = replay_state_;
    progress.total_entries = replay_entries_.size();
    progress.current_entry = replay_index_;
    progress.entries_replayed = entries_replayed_;
    progress.entries_skipped = entries_skipped_;
    progress.last_error = replay_error_;

    return progress;
}

const ExecutionLogEntry* ExecutionLogger::get_next_replay_entry() {
    std::lock_guard<std::mutex> lock(mutex_);

    if (replay_state_ != ReplayState::RUNNING) {
        return nullptr;
    }

    if (replay_index_ >= replay_entries_.size()) {
        replay_state_ = ReplayState::COMPLETED;
        spdlog::info("Replay completed (replayed={}, skipped={})",
                     entries_replayed_, entries_skipped_);
        return nullptr;
    }

    return &replay_entries_[replay_index_];
}

void ExecutionLogger::advance_replay(bool skipped) {
    std::lock_guard<std::mutex> lock(mutex_);

    if (replay_state_ != ReplayState::RUNNING) {
        return;
    }

    if (skipped) {
        entries_skipped_++;
    } else {
        entries_replayed_++;
    }

    replay_index_++;

    if (replay_index_ >= replay_entries_.size()) {
        replay_state_ = ReplayState::COMPLETED;
        spdlog::info("Replay completed (replayed={}, skipped={})",
                     entries_replayed_, entries_skipped_);
    }
}

void ExecutionLogger::set_config(const RecordingConfig& config) {
    std::lock_guard<std::mutex> lock(mutex_);
    config_ = config;
    trim_entries();
    spdlog::debug("ExecutionLogger config updated (max_entries={})", config_.max_entries);
}

void ExecutionLogger::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    entries_.clear();
    replay_entries_.clear();
    next_sequence_id_ = 1;
    recording_state_ = RecordingState::IDLE;
    replay_state_ = ReplayState::IDLE;
    spdlog::debug("ExecutionLogger cleared");
}

size_t ExecutionLogger::entry_count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return entries_.size();
}

uint64_t ExecutionLogger::last_sequence_id() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return next_sequence_id_ - 1;
}

void ExecutionLogger::trim_entries() {
    // Caller must hold the mutex
    while (entries_.size() > config_.max_entries) {
        entries_.pop_front();
    }
}

} // namespace agentos::kernel
