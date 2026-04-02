import { useState, useEffect, useCallback } from "react";
import api from "../api/client";
import s from "./SchemaChangesPage.module.css";

interface SchemaDiff {
  entity_type: string;
  field_name: string;
  change: string;
  old_type: string | null;
  new_type: string | null;
}

interface MigrationLog {
  id: number;
  detected_at: string;
  applied_at: string | null;
  entity_type: string;
  field_name: string;
  old_type: string;
  new_type: string;
  status: "detected" | "migrated" | "rolled_back" | "failed";
  migration_sql: string;
  rollback_sql: string;
  error_message: string;
}

export default function SchemaChangesPage() {
  const [differences, setDifferences] = useState<SchemaDiff[]>([]);
  const [history, setHistory] = useState<MigrationLog[]>([]);
  const [inSync, setInSync] = useState(true);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const [statusRes, historyRes] = await Promise.all([
        api.get("/admin-mgmt/schema/status/"),
        api.get("/admin-mgmt/schema/history/"),
      ]);
      setDifferences(statusRes.data.differences);
      setInSync(statusRes.data.in_sync);
      setHistory(historyRes.data);
    } catch {
      showMessage("Failed to load schema status", "error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  const showMessage = (text: string, type: "success" | "error") => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 3000);
  };

  const handleDetect = async () => {
    setDetecting(true);
    try {
      const res = await api.post("/admin-mgmt/schema/detect/", { auto_apply: true });
      const msg = res.data.message || "No schema changes detected";
      const applied = res.data.auto_applied ?? 0;
      showMessage(`${msg} (${applied} auto-applied)`, "success");
      fetchStatus();
    } catch {
      showMessage("Detection failed", "error");
    } finally {
      setDetecting(false);
    }
  };

  const handleApply = async (id: number) => {
    try {
      await api.post(`/admin-mgmt/schema/apply/${id}/`);
      showMessage("Migration applied", "success");
      fetchStatus();
    } catch {
      showMessage("Apply failed", "error");
    }
  };

  const handleRollback = async (id: number) => {
    try {
      await api.post(`/admin-mgmt/schema/rollback/${id}/`);
      showMessage("Rollback successful", "success");
      fetchStatus();
    } catch {
      showMessage("Rollback failed", "error");
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

  if (loading) {
    return (
      <div className={s.wrapper}>
        <div className={s.loadingContainer}>
          <div className={s.spinner} />
          <span className={s.loadingText}>Loading schema status...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={s.wrapper}>
      {message && (
        <div className={`${s.statusFlash} ${message.type === "success" ? s.statusSuccess : s.statusError}`}>
          {message.text}
        </div>
      )}

      <div className={s.header}>
        <h2 className={s.sectionTitle} style={{ margin: 0 }}>Migration History</h2>
        <div className={s.headerActions}>
          <span className={`${s.syncBadge} ${inSync ? s.syncBadgeOk : s.syncBadgeWarn}`}>
            {inSync ? "In Sync" : `${differences.length} Difference(s)`}
          </span>
          <button className={s.detectBtn} onClick={handleDetect} disabled={detecting}>
            {detecting ? "Detecting..." : "Detect & Auto-Migrate"}
            </button>
          </div>
      </div>
      <div className={s.tableCard}>
          <table className={s.table}>
            <thead>
              <tr>
                <th className={s.th}>Detected</th>
                <th className={s.th}>Entity</th>
                <th className={s.th}>Field</th>
                <th className={s.th}>Change</th>
                <th className={s.th}>Status</th>
                <th className={s.th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr><td className={s.td} colSpan={6}><div className={s.empty}>No schema migrations recorded yet.</div></td></tr>
              ) : history.map((m) => (
                <tr key={m.id} className={s.tr}>
                  <td className={s.td}>{formatDate(m.detected_at)}</td>
                  <td className={s.td}><span className={s.entityBadge}>{m.entity_type}</span></td>
                  <td className={s.td}><code className={s.fieldName}>{m.field_name}</code></td>
                  <td className={s.td}>{m.old_type} → {m.new_type}</td>
                  <td className={s.td}>
                    <span className={`${s.badge} ${
                      m.status === "detected" ? s.badgeDetected :
                      m.status === "migrated" ? s.badgeMigrated :
                      m.status === "rolled_back" ? s.badgeRolledBack :
                      s.badgeFailed
                    }`}>{m.status.replace("_", " ")}</span>
                  </td>
                  <td className={s.td}>
                    <div className={s.actionBtns}>
                      {m.status === "detected" && (
                        <button className={s.applyBtn} onClick={() => handleApply(m.id)}>Apply</button>
                      )}
                      {m.status === "migrated" && (
                        <button className={s.rollbackBtn} onClick={() => handleRollback(m.id)}>Rollback</button>
                      )}
                      {m.error_message && (
                        <span className={s.errorText} title={m.error_message}>Error</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
      </div>
    </div>
  );
}
