/**
 * Clove Audit Log
 *
 * Comprehensive logging system for security events, syscalls,
 * and agent activities. Supports categorized logging with
 * configurable retention and export capabilities.
 */
#pragma once
#include <string>
#include <vector>
#include <deque>
#include <mutex>
#include <chrono>
#include <unordered_set>
#include <cstdint>
#include <nlohmann/json.hpp>

namespace agentos::kernel {

// Audit event categories
enum class AuditCategory {
    SECURITY,         // Permission denied, blocked commands
    AGENT_LIFECYCLE,  // Spawn, kill, pause, resume
    IPC,              // Send, recv, broadcast
    STATE_STORE,      // Store, fetch, delete
    RESOURCE,         // Quota exceeded, resource warnings
    SYSCALL,          // All syscalls (verbose)
    NETWORK,          // HTTP requests, tunnel events
    WORLD             // World simulation events
};

// Convert AuditCategory to string
inline std::string audit_category_to_string(AuditCategory cat) {
    switch (cat) {
        case AuditCategory::SECURITY:        return "SECURITY";
        case AuditCategory::AGENT_LIFECYCLE: return "AGENT_LIFECYCLE";
        case AuditCategory::IPC:             return "IPC";
        case AuditCategory::STATE_STORE:     return "STATE_STORE";
        case AuditCategory::RESOURCE:        return "RESOURCE";
        case AuditCategory::SYSCALL:         return "SYSCALL";
        case AuditCategory::NETWORK:         return "NETWORK";
        case AuditCategory::WORLD:           return "WORLD";
        default: return "UNKNOWN";
    }
}

// Parse AuditCategory from string
inline AuditCategory audit_category_from_string(const std::string& str) {
    if (str == "SECURITY")        return AuditCategory::SECURITY;
    if (str == "AGENT_LIFECYCLE") return AuditCategory::AGENT_LIFECYCLE;
    if (str == "IPC")             return AuditCategory::IPC;
    if (str == "STATE_STORE")     return AuditCategory::STATE_STORE;
    if (str == "RESOURCE")        return AuditCategory::RESOURCE;
    if (str == "SYSCALL")         return AuditCategory::SYSCALL;
    if (str == "NETWORK")         return AuditCategory::NETWORK;
    if (str == "WORLD")           return AuditCategory::WORLD;
    return AuditCategory::SYSCALL;  // Default
}

// Audit log entry
struct AuditLogEntry {
    uint64_t id;                              // Unique entry ID
    std::chrono::system_clock::time_point timestamp;
    AuditCategory category;
    std::string event_type;                   // e.g., "SPAWN", "PERMISSION_DENIED"
    uint32_t agent_id;                        // Source agent (0 = kernel)
    std::string agent_name;                   // Agent name if known
    nlohmann::json details;                   // Event-specific details
    bool success;                             // Whether the operation succeeded

    // Convert to JSON
    nlohmann::json to_json() const;

    // Convert to JSONL (single line)
    std::string to_jsonl() const;
};

// Audit logger configuration
struct AuditConfig {
    size_t max_entries = 10000;               // Max entries in memory
    bool log_syscalls = false;                // Log ALL syscalls (verbose)
    bool log_security = true;                 // Log security events
    bool log_lifecycle = true;                // Log agent lifecycle events
    bool log_ipc = false;                     // Log IPC events
    bool log_state = false;                   // Log state store events
    bool log_resource = true;                 // Log resource events
    bool log_network = false;                 // Log network events
    bool log_world = false;                   // Log world events

    // Check if category is enabled
    bool is_enabled(AuditCategory cat) const;
};

// Audit logger class
class AuditLogger {
public:
    AuditLogger();
    explicit AuditLogger(const AuditConfig& config);
    ~AuditLogger() = default;

    // Log an event
    void log(AuditCategory category,
             const std::string& event_type,
             uint32_t agent_id,
             const std::string& agent_name,
             const nlohmann::json& details,
             bool success = true);

    // Convenience methods for common events
    void log_security(const std::string& event_type, uint32_t agent_id,
                      const std::string& agent_name, const nlohmann::json& details);
    void log_lifecycle(const std::string& event_type, uint32_t agent_id,
                       const std::string& agent_name, const nlohmann::json& details);
    void log_syscall(const std::string& syscall_name, uint32_t agent_id,
                     const nlohmann::json& payload, bool success);

    // Query methods
    std::vector<AuditLogEntry> get_entries(
        AuditCategory* category = nullptr,  // Filter by category (nullptr = all)
        uint32_t* agent_id = nullptr,       // Filter by agent (nullptr = all)
        uint64_t since_id = 0,              // Get entries after this ID
        size_t limit = 100                  // Max entries to return
    ) const;

    // Get entries by category string
    std::vector<AuditLogEntry> get_entries_by_category(
        const std::string& category,
        size_t limit = 100
    ) const;

    // Export to JSONL format
    std::string export_jsonl(size_t limit = 0) const;  // 0 = all entries

    // Configuration
    void set_config(const AuditConfig& config);
    const AuditConfig& get_config() const { return config_; }

    // Clear all entries
    void clear();

    // Get statistics
    size_t entry_count() const;
    uint64_t last_entry_id() const;

private:
    AuditConfig config_;
    std::deque<AuditLogEntry> entries_;
    mutable std::mutex mutex_;
    uint64_t next_id_ = 1;

    // Trim entries to max size
    void trim_entries();
};

} // namespace agentos::kernel
