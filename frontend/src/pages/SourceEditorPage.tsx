import { useState, useEffect, useCallback } from "react";
import api from "../api/client";
import s from "./SourceEditorPage.module.css";

/* ── Types ── */
interface Coach {
  id: number;
  name: string;
  email: string;
  is_active: boolean;
}

interface Account {
  id: number;
  name: string;
  industry: string;
  coach: number | null;
}

interface Contact {
  id: number;
  name: string;
  title: string;
  account_name: string;
  coach: number | null;
}

type TabKey = "coaches" | "accounts" | "contacts";

const TAB_LABELS: { key: TabKey; label: string }[] = [
  { key: "coaches", label: "Coaches" },
  { key: "accounts", label: "Accounts" },
  { key: "contacts", label: "Contacts" },
];

/* ── Component ── */
export default function SourceEditorPage() {
  const [coaches, setCoaches] = useState<Coach[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [tab, setTab] = useState<TabKey>("coaches");
  const [saveStatus, setSaveStatus] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);

  /* Fetch all source data */
  const fetchData = useCallback(async () => {
    try {
      const [cRes, aRes, tRes] = await Promise.all([
        api.get("/salesforce/coaches/"),
        api.get("/salesforce/accounts/"),
        api.get("/salesforce/contacts/"),
      ]);
      setCoaches(cRes.data);
      setAccounts(aRes.data);
      setContacts(tRes.data);
    } catch {
      showStatus("Failed to load source data", "error");
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  /* Status flash helper */
  const showStatus = (message: string, type: "success" | "error") => {
    setSaveStatus({ message, type });
    setTimeout(() => setSaveStatus(null), 2000);
  };

  /* ── Patch helpers ── */
  const updateCoach = async (id: number, field: string, value: unknown) => {
    try {
      await api.patch(`/salesforce/coaches/${id}/`, { [field]: value });
      showStatus("Saved", "success");
      fetchData();
    } catch {
      showStatus("Save failed", "error");
    }
  };

  const updateAccount = async (id: number, field: string, value: unknown) => {
    try {
      await api.patch(`/salesforce/accounts/${id}/`, { [field]: value });
      showStatus("Saved", "success");
      fetchData();
    } catch {
      showStatus("Save failed", "error");
    }
  };

  const updateContact = async (id: number, field: string, value: unknown) => {
    try {
      await api.patch(`/salesforce/contacts/${id}/`, { [field]: value });
      showStatus("Saved", "success");
      fetchData();
    } catch {
      showStatus("Save failed", "error");
    }
  };

  /* ── Render ── */
  return (
    <div className={s.wrapper}>
      {/* Header */}
      <div className={s.header}>
        {saveStatus && (
          <span
            className={`${s.saveStatus} ${
              saveStatus.type === "success"
                ? s.saveStatusSuccess
                : s.saveStatusError
            }`}
          >
            {saveStatus.message}
          </span>
        )}
        <p className={s.description}>
          Edit data below, then{" "}
          <span className={s.descriptionHighlight}>
            trigger a sync
          </span>{" "}
          to detect changes.
        </p>
      </div>

      {/* Tabs */}
      <div className={s.tabs}>
        {TAB_LABELS.map((t) => (
          <button
            key={t.key}
            className={`${s.tab} ${tab === t.key ? s.tabActive : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Coaches table */}
      {tab === "coaches" && (
        <div className={s.tableWrap}>
          {coaches.length === 0 ? (
            <div className={s.empty}>No coaches in source data</div>
          ) : (
            <table className={s.table}>
              <thead>
                <tr>
                  <th className={s.th}>Name</th>
                  <th className={s.th}>Email</th>
                  <th className={s.th}>Active</th>
                </tr>
              </thead>
              <tbody>
                {coaches.map((c) => (
                  <tr key={c.id} className={s.tr}>
                    <td className={s.td}>
                      <input
                        className={s.inlineInput}
                        value={c.name}
                        onChange={(e) =>
                          setCoaches((prev) =>
                            prev.map((x) =>
                              x.id === c.id
                                ? { ...x, name: e.target.value }
                                : x
                            )
                          )
                        }
                        onBlur={(e) => updateCoach(c.id, "name", e.target.value)}
                      />
                    </td>
                    <td className={s.td}>
                      <input
                        className={s.inlineInput}
                        value={c.email}
                        onChange={(e) =>
                          setCoaches((prev) =>
                            prev.map((x) =>
                              x.id === c.id
                                ? { ...x, email: e.target.value }
                                : x
                            )
                          )
                        }
                        onBlur={(e) =>
                          updateCoach(c.id, "email", e.target.value)
                        }
                      />
                    </td>
                    <td className={s.td}>
                      <input
                        type="checkbox"
                        className={s.checkbox}
                        checked={c.is_active}
                        onChange={(e) =>
                          updateCoach(c.id, "is_active", e.target.checked)
                        }
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Accounts table */}
      {tab === "accounts" && (
        <div className={s.tableWrap}>
          {accounts.length === 0 ? (
            <div className={s.empty}>No accounts in source data</div>
          ) : (
            <table className={s.table}>
              <thead>
                <tr>
                  <th className={s.th}>Account Name</th>
                  <th className={s.th}>Industry</th>
                  <th className={s.th}>Assigned Coach</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.id} className={s.tr}>
                    <td className={s.td}>
                      <input
                        className={s.inlineInput}
                        value={a.name}
                        onChange={(e) =>
                          setAccounts((prev) =>
                            prev.map((x) =>
                              x.id === a.id
                                ? { ...x, name: e.target.value }
                                : x
                            )
                          )
                        }
                        onBlur={(e) =>
                          updateAccount(a.id, "name", e.target.value)
                        }
                      />
                    </td>
                    <td className={s.td}>
                      <input
                        className={s.inlineInput}
                        value={a.industry}
                        onChange={(e) =>
                          setAccounts((prev) =>
                            prev.map((x) =>
                              x.id === a.id
                                ? { ...x, industry: e.target.value }
                                : x
                            )
                          )
                        }
                        onBlur={(e) =>
                          updateAccount(a.id, "industry", e.target.value)
                        }
                      />
                    </td>
                    <td className={s.td}>
                      <select
                        className={s.inlineSelect}
                        value={a.coach ?? ""}
                        onChange={(e) =>
                          updateAccount(
                            a.id,
                            "coach",
                            e.target.value ? Number(e.target.value) : null
                          )
                        }
                      >
                        <option value="">Unassigned</option>
                        {coaches.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Contacts table */}
      {tab === "contacts" && (
        <div className={s.tableWrap}>
          {contacts.length === 0 ? (
            <div className={s.empty}>No contacts in source data</div>
          ) : (
            <table className={s.table}>
              <thead>
                <tr>
                  <th className={s.th}>Name</th>
                  <th className={s.th}>Title</th>
                  <th className={s.th}>Account</th>
                  <th className={s.th}>Assigned Coach</th>
                </tr>
              </thead>
              <tbody>
                {contacts.map((c) => (
                  <tr key={c.id} className={s.tr}>
                    <td className={s.td}>
                      <input
                        className={s.inlineInput}
                        value={c.name}
                        onChange={(e) =>
                          setContacts((prev) =>
                            prev.map((x) =>
                              x.id === c.id
                                ? { ...x, name: e.target.value }
                                : x
                            )
                          )
                        }
                        onBlur={(e) =>
                          updateContact(c.id, "name", e.target.value)
                        }
                      />
                    </td>
                    <td className={s.td}>
                      <input
                        className={s.inlineInput}
                        value={c.title}
                        onChange={(e) =>
                          setContacts((prev) =>
                            prev.map((x) =>
                              x.id === c.id
                                ? { ...x, title: e.target.value }
                                : x
                            )
                          )
                        }
                        onBlur={(e) =>
                          updateContact(c.id, "title", e.target.value)
                        }
                      />
                    </td>
                    <td className={s.td}>{c.account_name}</td>
                    <td className={s.td}>
                      <select
                        className={s.inlineSelect}
                        value={c.coach ?? ""}
                        onChange={(e) =>
                          updateContact(
                            c.id,
                            "coach",
                            e.target.value ? Number(e.target.value) : null
                          )
                        }
                      >
                        <option value="">Unassigned</option>
                        {coaches.map((co) => (
                          <option key={co.id} value={co.id}>
                            {co.name}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
