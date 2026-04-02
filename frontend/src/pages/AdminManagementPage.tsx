import React, { useState, useEffect, useCallback, useRef } from 'react';
import api from '../api/client';
import s from './AdminManagementPage.module.css';

/* ────────────────────────── Types ────────────────────────── */

interface Coach {
  id: number; sf_id: string; name: string; email: string;
  active_clients: number; is_active: boolean; account_count: number; contact_count: number;
}
interface Account {
  id: number; sf_id: string; name: string; industry: string; website: string;
  coaching_start_date: string; coach: number; coach_name: string; contact_count: number;
}
interface Contact {
  id: number; sf_id: string; name: string; title: string; phone: string;
  email: string; account: number; account_name: string; coach: number; coach_name: string;
}

type Tab = 'coaches' | 'accounts' | 'contacts';

interface Flash { message: string; type: 'success' | 'error'; }

type ModalKind =
  | { kind: 'addCoach' }
  | { kind: 'addAccount' }
  | { kind: 'addContact' }
  | { kind: 'deleteConfirm'; entityType: string; entityName: string; onConfirm: () => void }
  | { kind: 'removeFromOrg'; coach: Coach }
  | { kind: 'swapCoaches' }
  | { kind: 'moveContact'; contact: Contact }
  | { kind: 'bulkReassign'; entityType: Tab; ids: number[] };

/* ────────────────────────── SVG Icons ────────────────────────── */

const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
);
const TrashIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2"/></svg>
);
const SwapIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 014-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 01-4 4H3"/></svg>
);
const MoveIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><polyline points="12 5 19 12 12 19"/></svg>
);

/* ────────────────────────── Component ────────────────────────── */

const AdminManagementPage: React.FC = () => {
  const [tab, setTab] = useState<Tab>('coaches');
  const [coaches, setCoaches] = useState<Coach[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [flash, setFlash] = useState<Flash | null>(null);
  const [modal, setModal] = useState<ModalKind | null>(null);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const flashTimer = useRef<ReturnType<typeof setTimeout>>();

  /* ── Flash helper ── */
  const showFlash = useCallback((message: string, type: 'success' | 'error' = 'success') => {
    if (flashTimer.current) clearTimeout(flashTimer.current);
    setFlash({ message, type });
    flashTimer.current = setTimeout(() => setFlash(null), 3000);
  }, []);

  /* ── Data fetching ── */
  const fetchAll = useCallback(async () => {
    try {
      const [c, a, ct] = await Promise.all([
        api.get('/admin-mgmt/coaches/'),
        api.get('/admin-mgmt/accounts/'),
        api.get('/admin-mgmt/contacts/'),
      ]);
      setCoaches(c.data); setAccounts(a.data); setContacts(ct.data);
    } catch { showFlash('Failed to load data', 'error'); }
  }, [showFlash]);

  useEffect(() => { fetchAll().finally(() => setLoading(false)); }, [fetchAll]);

  /* Clear selection on tab change */
  useEffect(() => { setSelected(new Set()); }, [tab]);

  /* ── Selection helpers ── */
  const currentItems = tab === 'coaches' ? coaches : tab === 'accounts' ? accounts : contacts;
  const allSelected = currentItems.length > 0 && selected.size === currentItems.length;

  const toggleOne = (id: number) => {
    setSelected(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  };
  const toggleAll = () => {
    if (allSelected) setSelected(new Set());
    else setSelected(new Set(currentItems.map(i => i.id)));
  };

  /* ── Inline edit helpers ── */
  const updateCoach = async (id: number, data: Partial<Coach>) => {
    try {
      await api.patch(`/admin-mgmt/coaches/${id}/update/`, data);
      showFlash('Coach updated'); await fetchAll();
    } catch { showFlash('Failed to update coach', 'error'); }
  };
  const updateAccount = async (id: number, data: Partial<Account>) => {
    try {
      await api.patch(`/admin-mgmt/accounts/${id}/update/`, data);
      showFlash('Account updated'); await fetchAll();
    } catch { showFlash('Failed to update account', 'error'); }
  };
  const updateContact = async (id: number, data: Partial<Contact>) => {
    try {
      await api.patch(`/admin-mgmt/contacts/${id}/update/`, data);
      showFlash('Contact updated'); await fetchAll();
    } catch { showFlash('Failed to update contact', 'error'); }
  };

  /* ── Delete helpers ── */
  const deleteCoach = async (id: number) => {
    try {
      await api.delete(`/admin-mgmt/coaches/${id}/delete/`);
      showFlash('Coach deleted'); await fetchAll();
    } catch { showFlash('Failed to delete coach', 'error'); }
  };
  const deleteAccount = async (id: number) => {
    try {
      await api.delete(`/admin-mgmt/accounts/${id}/delete/`);
      showFlash('Account deleted'); await fetchAll();
    } catch { showFlash('Failed to delete account', 'error'); }
  };
  const deleteContact = async (id: number) => {
    try {
      await api.delete(`/admin-mgmt/contacts/${id}/delete/`);
      showFlash('Contact deleted'); await fetchAll();
    } catch { showFlash('Failed to delete contact', 'error'); }
  };

  /* ── Reassign helpers ── */
  const reassignAccount = async (accountId: number, coachId: number) => {
    try {
      await api.post(`/admin-mgmt/accounts/${accountId}/reassign/`, { coach_id: coachId });
      showFlash('Account reassigned'); await fetchAll();
    } catch { showFlash('Failed to reassign account', 'error'); }
  };
  const reassignContact = async (contactId: number, coachId: number) => {
    try {
      await api.post(`/admin-mgmt/contacts/${contactId}/reassign/`, { coach_id: coachId });
      showFlash('Contact reassigned'); await fetchAll();
    } catch { showFlash('Failed to reassign contact', 'error'); }
  };

  /* ── Bulk delete ── */
  const bulkDelete = async () => {
    const ids = Array.from(selected);
    try {
      if (tab === 'coaches') await Promise.all(ids.map(id => api.delete(`/admin-mgmt/coaches/${id}/delete/`)));
      else if (tab === 'accounts') await Promise.all(ids.map(id => api.delete(`/admin-mgmt/accounts/${id}/delete/`)));
      else await Promise.all(ids.map(id => api.delete(`/admin-mgmt/contacts/${id}/delete/`)));
      showFlash(`${ids.length} item(s) deleted`);
      setSelected(new Set()); await fetchAll();
    } catch { showFlash('Bulk delete failed', 'error'); }
  };

  /* ────────────────── Inline Editable Cell ────────────────── */
  const EditableCell: React.FC<{ value: string; onSave: (v: string) => void }> = ({ value, onSave }) => {
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState(value);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => { if (editing) inputRef.current?.focus(); }, [editing]);
    useEffect(() => { setDraft(value); }, [value]);

    if (!editing) return <span onDoubleClick={() => setEditing(true)} style={{ cursor: 'pointer' }}>{value}</span>;
    return (
      <input
        ref={inputRef}
        className={s.inlineInput}
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={() => { setEditing(false); if (draft !== value) onSave(draft); }}
        onKeyDown={e => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); if (e.key === 'Escape') { setDraft(value); setEditing(false); } }}
      />
    );
  };

  /* ────────────────── Coach Select (inline) ────────────────── */
  const CoachSelect: React.FC<{ currentCoachId: number; onChange: (id: number) => void }> = ({ currentCoachId, onChange }) => (
    <select
      className={s.inlineSelect}
      value={currentCoachId}
      onChange={e => { const v = Number(e.target.value); if (v !== currentCoachId) onChange(v); }}
    >
      {coaches.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
    </select>
  );

  /* ────────────────── Tables ────────────────── */
  const renderCoachTable = () => (
    <table className={s.table}>
      <thead>
        <tr>
          <th className={`${s.th} ${s.thCheckbox}`}><input type="checkbox" className={s.checkbox} checked={allSelected} onChange={toggleAll} /></th>
          <th className={s.th}>Name</th><th className={s.th}>Email</th>
          <th className={s.th}>Active Clients</th><th className={s.th}>Status</th>
          <th className={s.th}>Accounts</th><th className={s.th}>Contacts</th>
          <th className={s.th}>Actions</th>
        </tr>
      </thead>
      <tbody>
        {coaches.map(c => (
          <tr key={c.id} className={`${s.tr} ${selected.has(c.id) ? s.trSelected : ''}`}>
            <td className={`${s.td} ${s.tdCheckbox}`}><input type="checkbox" className={s.checkbox} checked={selected.has(c.id)} onChange={() => toggleOne(c.id)} /></td>
            <td className={s.td}><EditableCell value={c.name} onSave={v => updateCoach(c.id, { name: v })} /></td>
            <td className={s.td}><EditableCell value={c.email} onSave={v => updateCoach(c.id, { email: v })} /></td>
            <td className={s.td}>{c.active_clients}</td>
            <td className={s.td}><span className={`${s.badge} ${c.is_active ? s.badgeActive : s.badgeInactive}`}>{c.is_active ? 'Active' : 'Inactive'}</span></td>
            <td className={s.td}>{c.account_count}</td>
            <td className={s.td}>{c.contact_count}</td>
            <td className={s.td}>
              <div className={s.actionBtns}>
                <button className={`${s.iconBtn} ${s.iconBtnDanger}`} title="Delete" onClick={() => setModal({ kind: 'deleteConfirm', entityType: 'Coach', entityName: c.name, onConfirm: () => deleteCoach(c.id) })}><TrashIcon /></button>
                <button className={s.iconBtn} title="Remove from Org" onClick={() => setModal({ kind: 'removeFromOrg', coach: c })}><MoveIcon /></button>
              </div>
            </td>
          </tr>
        ))}
        {coaches.length === 0 && <tr><td className={s.empty} colSpan={8}>No coaches found</td></tr>}
      </tbody>
    </table>
  );

  const renderAccountTable = () => (
    <table className={s.table}>
      <thead>
        <tr>
          <th className={`${s.th} ${s.thCheckbox}`}><input type="checkbox" className={s.checkbox} checked={allSelected} onChange={toggleAll} /></th>
          <th className={s.th}>Name</th><th className={s.th}>Industry</th>
          <th className={s.th}>Coach</th><th className={s.th}>Contacts</th>
          <th className={s.th}>Actions</th>
        </tr>
      </thead>
      <tbody>
        {accounts.map(a => (
          <tr key={a.id} className={`${s.tr} ${selected.has(a.id) ? s.trSelected : ''}`}>
            <td className={`${s.td} ${s.tdCheckbox}`}><input type="checkbox" className={s.checkbox} checked={selected.has(a.id)} onChange={() => toggleOne(a.id)} /></td>
            <td className={s.td}><EditableCell value={a.name} onSave={v => updateAccount(a.id, { name: v })} /></td>
            <td className={s.td}><EditableCell value={a.industry} onSave={v => updateAccount(a.id, { industry: v })} /></td>
            <td className={s.td}><CoachSelect currentCoachId={a.coach} onChange={id => reassignAccount(a.id, id)} /></td>
            <td className={s.td}>{a.contact_count}</td>
            <td className={s.td}>
              <div className={s.actionBtns}>
                <button className={`${s.iconBtn} ${s.iconBtnDanger}`} title="Delete" onClick={() => setModal({ kind: 'deleteConfirm', entityType: 'Account', entityName: a.name, onConfirm: () => deleteAccount(a.id) })}><TrashIcon /></button>
              </div>
            </td>
          </tr>
        ))}
        {accounts.length === 0 && <tr><td className={s.empty} colSpan={6}>No accounts found</td></tr>}
      </tbody>
    </table>
  );

  const renderContactTable = () => (
    <table className={s.table}>
      <thead>
        <tr>
          <th className={`${s.th} ${s.thCheckbox}`}><input type="checkbox" className={s.checkbox} checked={allSelected} onChange={toggleAll} /></th>
          <th className={s.th}>Name</th><th className={s.th}>Title</th>
          <th className={s.th}>Email</th><th className={s.th}>Account</th>
          <th className={s.th}>Coach</th><th className={s.th}>Actions</th>
        </tr>
      </thead>
      <tbody>
        {contacts.map(ct => (
          <tr key={ct.id} className={`${s.tr} ${selected.has(ct.id) ? s.trSelected : ''}`}>
            <td className={`${s.td} ${s.tdCheckbox}`}><input type="checkbox" className={s.checkbox} checked={selected.has(ct.id)} onChange={() => toggleOne(ct.id)} /></td>
            <td className={s.td}><EditableCell value={ct.name} onSave={v => updateContact(ct.id, { name: v })} /></td>
            <td className={s.td}><EditableCell value={ct.title} onSave={v => updateContact(ct.id, { title: v })} /></td>
            <td className={s.td}><EditableCell value={ct.email} onSave={v => updateContact(ct.id, { email: v })} /></td>
            <td className={s.td}>{ct.account_name}</td>
            <td className={s.td}><CoachSelect currentCoachId={ct.coach} onChange={id => reassignContact(ct.id, id)} /></td>
            <td className={s.td}>
              <div className={s.actionBtns}>
                <button className={s.iconBtn} title="Move to Account" onClick={() => setModal({ kind: 'moveContact', contact: ct })}><MoveIcon /></button>
                <button className={`${s.iconBtn} ${s.iconBtnDanger}`} title="Delete" onClick={() => setModal({ kind: 'deleteConfirm', entityType: 'Contact', entityName: ct.name, onConfirm: () => deleteContact(ct.id) })}><TrashIcon /></button>
              </div>
            </td>
          </tr>
        ))}
        {contacts.length === 0 && <tr><td className={s.empty} colSpan={7}>No contacts found</td></tr>}
      </tbody>
    </table>
  );

  /* ────────────────── Modals ────────────────── */

  const AddCoachModal: React.FC = () => {
    const [form, setForm] = useState({ name: '', email: '', is_active: true });
    const [error, setError] = useState('');
    const submit = async () => {
      if (!form.name || !form.email) { setError('Name and email are required'); return; }
      try {
        await api.post('/admin-mgmt/coaches/create/', form);
        showFlash('Coach created'); setModal(null); fetchAll();
      } catch { setError('Failed to create coach'); }
    };
    return (
      <div className={s.modalOverlay} onClick={() => setModal(null)}>
        <div className={s.modalCard} onClick={e => e.stopPropagation()}>
          <h2 className={s.modalTitle}>Add Coach</h2>
          <div className={s.modalField}><label className={s.modalLabel}>Name</label><input className={s.modalInput} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div className={s.modalField}><label className={s.modalLabel}>Email</label><input className={s.modalInput} type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Status</label>
            <select className={s.modalSelect} value={form.is_active ? 'true' : 'false'} onChange={e => setForm({ ...form, is_active: e.target.value === 'true' })}>
              <option value="true">Active</option><option value="false">Inactive</option>
            </select>
          </div>
          {error && <p className={s.formError}>{error}</p>}
          <div className={s.modalFooter}>
            <button className={s.modalCancelBtn} onClick={() => setModal(null)}>Cancel</button>
            <button className={s.modalSubmitBtn} onClick={submit}>Create</button>
          </div>
        </div>
      </div>
    );
  };

  const AddAccountModal: React.FC = () => {
    const [form, setForm] = useState({ name: '', industry: '', website: '', coach: coaches[0]?.id ?? 0 });
    const [error, setError] = useState('');
    const submit = async () => {
      if (!form.name) { setError('Name is required'); return; }
      try {
        await api.post('/admin-mgmt/accounts/create/', form);
        showFlash('Account created'); setModal(null); fetchAll();
      } catch { setError('Failed to create account'); }
    };
    return (
      <div className={s.modalOverlay} onClick={() => setModal(null)}>
        <div className={s.modalCard} onClick={e => e.stopPropagation()}>
          <h2 className={s.modalTitle}>Add Account</h2>
          <div className={s.modalField}><label className={s.modalLabel}>Name</label><input className={s.modalInput} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div className={s.modalField}><label className={s.modalLabel}>Industry</label><input className={s.modalInput} value={form.industry} onChange={e => setForm({ ...form, industry: e.target.value })} /></div>
          <div className={s.modalField}><label className={s.modalLabel}>Website</label><input className={s.modalInput} value={form.website} onChange={e => setForm({ ...form, website: e.target.value })} /></div>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Coach</label>
            <select className={s.modalSelect} value={form.coach} onChange={e => setForm({ ...form, coach: Number(e.target.value) })}>
              {coaches.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          {error && <p className={s.formError}>{error}</p>}
          <div className={s.modalFooter}>
            <button className={s.modalCancelBtn} onClick={() => setModal(null)}>Cancel</button>
            <button className={s.modalSubmitBtn} onClick={submit}>Create</button>
          </div>
        </div>
      </div>
    );
  };

  const AddContactModal: React.FC = () => {
    const [form, setForm] = useState({ name: '', title: '', email: '', phone: '', account: accounts[0]?.id ?? 0, coach: coaches[0]?.id ?? 0 });
    const [error, setError] = useState('');
    const submit = async () => {
      if (!form.name) { setError('Name is required'); return; }
      try {
        await api.post('/admin-mgmt/contacts/create/', form);
        showFlash('Contact created'); setModal(null); fetchAll();
      } catch { setError('Failed to create contact'); }
    };
    return (
      <div className={s.modalOverlay} onClick={() => setModal(null)}>
        <div className={s.modalCard} onClick={e => e.stopPropagation()}>
          <h2 className={s.modalTitle}>Add Contact</h2>
          <div className={s.modalField}><label className={s.modalLabel}>Name</label><input className={s.modalInput} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
          <div className={s.modalField}><label className={s.modalLabel}>Title</label><input className={s.modalInput} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></div>
          <div className={s.modalField}><label className={s.modalLabel}>Email</label><input className={s.modalInput} type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></div>
          <div className={s.modalField}><label className={s.modalLabel}>Phone</label><input className={s.modalInput} value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} /></div>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Account</label>
            <select className={s.modalSelect} value={form.account} onChange={e => setForm({ ...form, account: Number(e.target.value) })}>
              {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Coach</label>
            <select className={s.modalSelect} value={form.coach} onChange={e => setForm({ ...form, coach: Number(e.target.value) })}>
              {coaches.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          {error && <p className={s.formError}>{error}</p>}
          <div className={s.modalFooter}>
            <button className={s.modalCancelBtn} onClick={() => setModal(null)}>Cancel</button>
            <button className={s.modalSubmitBtn} onClick={submit}>Create</button>
          </div>
        </div>
      </div>
    );
  };

  const DeleteConfirmModal: React.FC<{ entityType: string; entityName: string; onConfirm: () => void }> = ({ entityType, entityName, onConfirm }) => (
    <div className={s.modalOverlay} onClick={() => setModal(null)}>
      <div className={s.modalCard} onClick={e => e.stopPropagation()}>
        <h2 className={s.modalTitle}>Delete {entityType}</h2>
        <p className={s.description}>Are you sure you want to delete <strong>{entityName}</strong>? This action cannot be undone.</p>
        <div className={s.modalFooter}>
          <button className={s.modalCancelBtn} onClick={() => setModal(null)}>Cancel</button>
          <button className={s.modalDangerBtn} onClick={() => { onConfirm(); setModal(null); }}>Delete</button>
        </div>
      </div>
    </div>
  );

  const RemoveFromOrgModal: React.FC<{ coach: Coach }> = ({ coach }) => {
    const [redistributeTo, setRedistributeTo] = useState<Set<number>>(new Set());
    const [error, setError] = useState('');
    const otherCoaches = coaches.filter(c => c.id !== coach.id);

    const toggleCoach = (id: number) => {
      setRedistributeTo(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
    };

    const submit = async () => {
      try {
        await api.post('/admin-mgmt/coaches/remove-from-org/', {
          coach_id: coach.id,
          redistribute_to: Array.from(redistributeTo),
        });
        showFlash(`${coach.name} removed from org`); setModal(null); fetchAll();
      } catch { setError('Failed to remove coach from org'); }
    };

    return (
      <div className={s.modalOverlay} onClick={() => setModal(null)}>
        <div className={s.modalCard} onClick={e => e.stopPropagation()}>
          <h2 className={s.modalTitle}>Remove {coach.name} from Org</h2>
          <p className={s.description}>This will deactivate the coach. Optionally, redistribute their clients to other coaches:</p>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Redistribute to (optional)</label>
            <div className={s.coachList}>
              {otherCoaches.map(c => (
                <div key={c.id} className={`${s.coachItem} ${redistributeTo.has(c.id) ? s.coachItemSelected : ''}`} onClick={() => toggleCoach(c.id)}>
                  <input type="checkbox" className={s.checkbox} checked={redistributeTo.has(c.id)} readOnly />
                  <div>
                    <div className={s.coachItemName}>{c.name}</div>
                    <div className={s.coachItemEmail}>{c.email}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          {error && <p className={s.formError}>{error}</p>}
          <div className={s.modalFooter}>
            <button className={s.modalCancelBtn} onClick={() => setModal(null)}>Cancel</button>
            <button className={s.modalDangerBtn} onClick={submit}>Remove</button>
          </div>
        </div>
      </div>
    );
  };

  const SwapCoachesModal: React.FC = () => {
    const [coachA, setCoachA] = useState(coaches[0]?.id ?? 0);
    const [coachB, setCoachB] = useState(coaches[1]?.id ?? 0);
    const [error, setError] = useState('');
    const submit = async () => {
      if (coachA === coachB) { setError('Select two different coaches'); return; }
      try {
        await api.post('/admin-mgmt/bulk/swap-coaches/', { swaps: [{ coach_id: coachA, target_coach_id: coachB }] });
        showFlash('Coaches swapped'); setModal(null); fetchAll();
      } catch { setError('Failed to swap coaches'); }
    };
    return (
      <div className={s.modalOverlay} onClick={() => setModal(null)}>
        <div className={s.modalCard} onClick={e => e.stopPropagation()}>
          <h2 className={s.modalTitle}>Swap Coaches</h2>
          <p className={s.description}>All accounts and contacts of Coach A will be assigned to Coach B and vice versa.</p>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Coach A</label>
            <select className={s.modalSelect} value={coachA} onChange={e => setCoachA(Number(e.target.value))}>
              {coaches.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Coach B</label>
            <select className={s.modalSelect} value={coachB} onChange={e => setCoachB(Number(e.target.value))}>
              {coaches.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          {error && <p className={s.formError}>{error}</p>}
          <div className={s.modalFooter}>
            <button className={s.modalCancelBtn} onClick={() => setModal(null)}>Cancel</button>
            <button className={s.modalSubmitBtn} onClick={submit}>Swap</button>
          </div>
        </div>
      </div>
    );
  };

  const MoveContactModal: React.FC<{ contact: Contact }> = ({ contact }) => {
    const [targetAccount, setTargetAccount] = useState(contact.account);
    const [targetCoach, setTargetCoach] = useState<number | ''>('');
    const [error, setError] = useState('');
    const submit = async () => {
      try {
        const payload: { target_account_id: number; target_coach_id?: number } = { target_account_id: targetAccount };
        if (targetCoach !== '') payload.target_coach_id = targetCoach;
        await api.post(`/admin-mgmt/contacts/${contact.id}/move/`, payload);
        showFlash('Contact moved'); setModal(null); fetchAll();
      } catch { setError('Failed to move contact'); }
    };
    return (
      <div className={s.modalOverlay} onClick={() => setModal(null)}>
        <div className={s.modalCard} onClick={e => e.stopPropagation()}>
          <h2 className={s.modalTitle}>Move {contact.name}</h2>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Target Account</label>
            <select className={s.modalSelect} value={targetAccount} onChange={e => setTargetAccount(Number(e.target.value))}>
              {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Target Coach (optional)</label>
            <select className={s.modalSelect} value={targetCoach} onChange={e => setTargetCoach(e.target.value === '' ? '' : Number(e.target.value))}>
              <option value="">Keep current coach</option>
              {coaches.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          {error && <p className={s.formError}>{error}</p>}
          <div className={s.modalFooter}>
            <button className={s.modalCancelBtn} onClick={() => setModal(null)}>Cancel</button>
            <button className={s.modalSubmitBtn} onClick={submit}>Move</button>
          </div>
        </div>
      </div>
    );
  };

  const BulkReassignModal: React.FC<{ entityType: Tab; ids: number[] }> = ({ entityType, ids }) => {
    const [targetCoach, setTargetCoach] = useState(coaches[0]?.id ?? 0);
    const [error, setError] = useState('');
    const submit = async () => {
      try {
        await api.post('/admin-mgmt/bulk/reassign/', { entity_type: entityType, entity_ids: ids, target_coach_id: targetCoach });
        showFlash(`${ids.length} item(s) reassigned`); setModal(null); setSelected(new Set()); fetchAll();
      } catch { setError('Bulk reassign failed'); }
    };
    return (
      <div className={s.modalOverlay} onClick={() => setModal(null)}>
        <div className={s.modalCard} onClick={e => e.stopPropagation()}>
          <h2 className={s.modalTitle}>Bulk Reassign</h2>
          <p className={s.description}>Reassign {ids.length} selected {entityType} to a new coach.</p>
          <div className={s.modalField}>
            <label className={s.modalLabel}>Target Coach</label>
            <select className={s.modalSelect} value={targetCoach} onChange={e => setTargetCoach(Number(e.target.value))}>
              {coaches.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          {error && <p className={s.formError}>{error}</p>}
          <div className={s.modalFooter}>
            <button className={s.modalCancelBtn} onClick={() => setModal(null)}>Cancel</button>
            <button className={s.modalSubmitBtn} onClick={submit}>Reassign</button>
          </div>
        </div>
      </div>
    );
  };

  /* ────────────────── Render modal by kind ────────────────── */
  const renderModal = () => {
    if (!modal) return null;
    switch (modal.kind) {
      case 'addCoach': return <AddCoachModal />;
      case 'addAccount': return <AddAccountModal />;
      case 'addContact': return <AddContactModal />;
      case 'deleteConfirm': return <DeleteConfirmModal entityType={modal.entityType} entityName={modal.entityName} onConfirm={modal.onConfirm} />;
      case 'removeFromOrg': return <RemoveFromOrgModal coach={modal.coach} />;
      case 'swapCoaches': return <SwapCoachesModal />;
      case 'moveContact': return <MoveContactModal contact={modal.contact} />;
      case 'bulkReassign': return <BulkReassignModal entityType={modal.entityType} ids={modal.ids} />;
    }
  };

  /* ────────────────── Add button per tab ────────────────── */
  const addModalKind: Record<Tab, ModalKind> = {
    coaches: { kind: 'addCoach' },
    accounts: { kind: 'addAccount' },
    contacts: { kind: 'addContact' },
  };

  /* ────────────────── Main render ────────────────── */
  if (loading) {
    return (
      <div className={s.wrapper}>
        <div className={s.loadingContainer}>
          <div className={s.spinner} />
          <p className={s.loadingText}>Loading management data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className={s.wrapper}>
      {/* Flash */}
      {flash && (
        <div className={`${s.statusFlash} ${flash.type === 'success' ? s.statusSuccess : s.statusError}`}>
          {flash.message}
        </div>
      )}

      {/* Tabs + Action Buttons row */}
      <div className={s.header}>
        <div className={s.tabs}>
          {(['coaches', 'accounts', 'contacts'] as Tab[]).map(t => (
            <button key={t} className={`${s.tab} ${tab === t ? s.tabActive : ''}`} onClick={() => setTab(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
        <div className={s.headerActions}>
          <button className={s.addBtn} onClick={() => setModal(addModalKind[tab])}><PlusIcon /> Add {tab === 'coaches' ? 'Coach' : tab === 'accounts' ? 'Account' : 'Contact'}</button>
          <button className={s.secondaryBtn} onClick={() => setModal({ kind: 'swapCoaches' })}><SwapIcon /> Swap Coaches</button>
        </div>
      </div>

      {/* Bulk toolbar */}
      {selected.size > 0 && (
        <div className={s.toolbar}>
          <span className={s.toolbarText}>{selected.size} selected</span>
          <div className={s.toolbarActions}>
            <button className={s.secondaryBtn} onClick={() => setModal({ kind: 'bulkReassign', entityType: tab, ids: Array.from(selected) })}>Bulk Reassign</button>
            <button className={s.dangerBtn} onClick={() => setModal({ kind: 'deleteConfirm', entityType: tab, entityName: `${selected.size} item(s)`, onConfirm: bulkDelete })}>
              <TrashIcon /> Delete Selected
            </button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className={s.tableCard}>
        {tab === 'coaches' && renderCoachTable()}
        {tab === 'accounts' && renderAccountTable()}
        {tab === 'contacts' && renderContactTable()}
      </div>

      {/* Modals */}
      {renderModal()}
    </div>
  );
};

export default AdminManagementPage;
