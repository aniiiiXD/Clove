#include "kernel/audit_log.hpp"
#include <spdlog/spdlog.h>
#include <iomanip>
#include <sstream>

namespace agentos::kernel {

using json = nlohmann::json;

// ============================================================================
// AuditLogEntry Implementation
// ============================================================================

json AuditLogEntry::to_json() const {
    json j;
    j["id"] = id;

    // Format timestamp as ISO 8601
    auto time_t = std::chrono::system_clock::to_time_t(timestamp);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        timestamp.time_since_epoch()) % 1000;
    std::ostringstream oss;
    oss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%S");
    oss << '.' << std::setfill('0') << std::setw(3) << ms.count() << 'Z';
    j["timestamp"] = oss.str();

    j["category"] = audit_category_to_string(category);
    j["event_type"] = event_type;
    j["agent_id"] = agent_id;
    if (!agent_name.empty()) {
        j["agent_name"] = agent_name;
    }
    j["success"] = success;
    j["details"] = details;

    return j;
}

std::string AuditLogEntry::to_jsonl() const {
    return to_json().dump() + "\n";
}

// ============================================================================
// AuditConfig Implementation
// ============================================================================

bool AuditConfig::is_enabled(AuditCategory cat) const {
    switch (cat) {
        case AuditCategory::SECURITY:        return log_security;
        case AuditCategory::AGENT_LIFECYCLE: return log_lifecycle;
        case AuditCategory::IPC:             return log_ipc;
        case AuditCategory::STATE_STORE:     return log_state;
        case AuditCategory::RESOURCE:        return log_resource;
        case AuditCategory::SYSCALL:         return log_syscalls;
        case AuditCategory::NETWORK:         return log_network;
        case AuditCategory::WORLD:           return log_world;
        default: return false;
    }
}

// ============================================================================
// AuditLogger Implementation
// ============================================================================

AuditLogger::AuditLogger() : config_() {
    spdlog::debug("AuditLogger initialized with default config");
}

AuditLogger::AuditLogger(const AuditConfig& config) : config_(config) {
    spdlog::debug("AuditLogger initialized (max_entries={})", config_.max_entries);
}

void AuditLogger::log(AuditCategory category,
                      const std::string& event_type,
                      uint32_t agent_id,
                      const std::string& agent_name,
                      const json& details,
                      bool success) {
    // Check if category is enabled
    if (!config_.is_enabled(category)) {
        return;
    }

    std::lock_guard<std::mutex> lock(mutex_);

    AuditLogEntry entry;
    entry.id = next_id_++;
    entry.timestamp = std::chrono::system_clock::now();
    entry.category = category;
    entry.event_type = event_type;
    entry.agent_id = agent_id;
    entry.agent_name = agent_name;
    entry.details = details;
    entry.success = success;

    entries_.push_back(entry);
    trim_entries();

    spdlog::trace("Audit[{}]: {} agent_id={} success={}",
                  audit_category_to_string(category),
                  event_type, agent_id, success);
}

void AuditLogger::log_security(const std::string& event_type,
                               uint32_t agent_id,
                               const std::string& agent_name,
                               const json& details) {
    log(AuditCategory::SECURITY, event_type, agent_id, agent_name, details, false);
}

void AuditLogger::log_lifecycle(const std::string& event_type,
                                uint32_t agent_id,
                                const std::string& agent_name,
                                const json& details) {
    log(AuditCategory::AGENT_LIFECYCLE, event_type, agent_id, agent_name, details, true);
}

void AuditLogger::log_syscall(const std::string& syscall_name,
                              uint32_t agent_id,
                              const json& payload,
                              bool success) {
    json details;
    details["syscall"] = syscall_name;
    if (!payload.empty()) {
        details["payload"] = payload;
    }
    log(AuditCategory::SYSCALL, syscall_name, agent_id, "", details, success);
}

std::vector<AuditLogEntry> AuditLogger::get_entries(
    AuditCategory* category,
    uint32_t* agent_id,
    uint64_t since_id,
    size_t limit) const {

    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<AuditLogEntry> result;

    for (auto it = entries_.rbegin(); it != entries_.rend() && result.size() < limit; ++it) {
        const auto& entry = *it;

        // Filter by since_id
        if (entry.id <= since_id) {
            continue;
        }

        // Filter by category
        if (category && entry.category != *category) {
            continue;
        }

        // Filter by agent_id
        if (agent_id && entry.agent_id != *agent_id) {
            continue;
        }

        result.push_back(entry);
    }

    // Reverse to get chronological order
    std::reverse(result.begin(), result.end());
    return result;
}

std::vector<AuditLogEntry> AuditLogger::get_entries_by_category(
    const std::string& category,
    size_t limit) const {

    AuditCategory cat = audit_category_from_string(category);
    return get_entries(&cat, nullptr, 0, limit);
}

std::string AuditLogger::export_jsonl(size_t limit) const {
    std::lock_guard<std::mutex> lock(mutex_);
    std::ostringstream oss;

    size_t count = 0;
    for (const auto& entry : entries_) {
        if (limit > 0 && count >= limit) {
            break;
        }
        oss << entry.to_jsonl();
        count++;
    }

    return oss.str();
}

void AuditLogger::set_config(const AuditConfig& config) {
    std::lock_guard<std::mutex> lock(mutex_);
    config_ = config;
    trim_entries();
    spdlog::debug("AuditLogger config updated (max_entries={})", config_.max_entries);
}

void AuditLogger::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    entries_.clear();
    spdlog::debug("AuditLogger cleared");
}

size_t AuditLogger::entry_count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return entries_.size();
}

uint64_t AuditLogger::last_entry_id() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return next_id_ - 1;
}

void AuditLogger::trim_entries() {
    // Caller must hold the mutex
    while (entries_.size() > config_.max_entries) {
        entries_.pop_front();
    }
}

} // namespace agentos::kernel
