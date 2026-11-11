import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import {
  addActionItem,
  deleteActionItem,
  getMeeting,
  summarizeMeeting,
  updateActionItem,
  updateMeeting,
} from "../../api/meetings";
import { extractErrorMessage } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import type { Meeting } from "../../types";
import { formatDateTime } from "../../utils/format";

export function MeetingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const meetingId = Number(id);
  const navigate = useNavigate();
  const { user } = useAuth();

  const [meeting, setMeeting] = useState<Meeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summarizing, setSummarizing] = useState(false);

  const [rawNotes, setRawNotes] = useState("");
  const [savingNotes, setSavingNotes] = useState(false);

  const [description, setDescription] = useState("");
  const [assignee, setAssignee] = useState("");
  const [addingItem, setAddingItem] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await getMeeting(meetingId);
      setMeeting(res.data);
      setRawNotes(res.data.raw_notes);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meetingId]);

  const canModify = !!meeting && !!user && (user.id === meeting.created_by.id || user.role === "admin");

  async function handleSummarize() {
    setError(null);
    setSummarizing(true);
    try {
      const res = await summarizeMeeting(meetingId);
      setMeeting(res.data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSummarizing(false);
    }
  }

  async function handleSaveNotes(e: FormEvent) {
    e.preventDefault();
    if (!meeting) return;
    setError(null);
    setSavingNotes(true);
    try {
      const res = await updateMeeting(meetingId, {
        title: meeting.title,
        meeting_date: meeting.meeting_date,
        raw_notes: rawNotes,
      });
      setMeeting(res.data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSavingNotes(false);
    }
  }

  async function handleAddActionItem(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setAddingItem(true);
    try {
      await addActionItem(meetingId, { description, assignee: assignee || null });
      setDescription("");
      setAssignee("");
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setAddingItem(false);
    }
  }

  async function handleToggleDone(itemId: number, isDone: boolean) {
    setError(null);
    try {
      await updateActionItem(itemId, { is_done: !isDone });
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleDeleteActionItem(itemId: number) {
    setError(null);
    try {
      await deleteActionItem(itemId);
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  if (loading) return <p>Loading...</p>;
  if (!meeting) return <p>Meeting not found.</p>;

  return (
    <div>
      <div className="page-header">
        <h1>{meeting.title}</h1>
        <div className="actions">
          <button onClick={handleSummarize} disabled={summarizing}>
            {summarizing ? "Summarizing..." : meeting.summary ? "Re-summarize" : "Summarize"}
          </button>
          <button className="secondary" onClick={() => navigate("/")}>Back to meetings</button>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="card">
        <div className="summary-grid">
          <div className="summary-tile">
            <div className="label">Date</div>
            <div className="value">{meeting.meeting_date}</div>
          </div>
          <div className="summary-tile">
            <div className="label">Created by</div>
            <div className="value">{meeting.created_by.full_name || meeting.created_by.email}</div>
          </div>
          <div className="summary-tile">
            <div className="label">Action items</div>
            <div className="value">{meeting.action_items.length}</div>
          </div>
        </div>

        <h2>AI summary</h2>
        {meeting.summary ? (
          <>
            <p>{meeting.summary.summary}</p>
            <p className="muted">Generated {formatDateTime(meeting.summary.generated_at)}</p>
          </>
        ) : (
          <p className="muted">Not summarized yet. Click "Summarize" above.</p>
        )}
      </div>

      <div className="card">
        <h2>Raw notes</h2>
        <form onSubmit={handleSaveNotes}>
          <textarea
            rows={8}
            style={{ width: "100%" }}
            value={rawNotes}
            onChange={(e) => setRawNotes(e.target.value)}
            disabled={!canModify}
          />
          {canModify && (
            <button type="submit" disabled={savingNotes} style={{ marginTop: "0.5rem" }}>
              {savingNotes ? "Saving..." : "Save notes"}
            </button>
          )}
        </form>
      </div>

      <div className="card">
        <h2>Action items</h2>
        <table>
          <thead>
            <tr>
              <th>Done</th>
              <th>Description</th>
              <th>Assignee</th>
              <th>Source</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {meeting.action_items.map((item) => (
              <tr key={item.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={item.is_done}
                    onChange={() => handleToggleDone(item.id, item.is_done)}
                  />
                </td>
                <td className={item.is_done ? "muted" : undefined}>{item.description}</td>
                <td>{item.assignee || <span className="muted">Unassigned</span>}</td>
                <td>{item.is_ai_generated ? "AI" : "Manual"}</td>
                <td className="actions">
                  <button className="danger" onClick={() => handleDeleteActionItem(item.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {meeting.action_items.length === 0 && (
              <tr><td colSpan={5} className="muted">No action items yet.</td></tr>
            )}
          </tbody>
        </table>
        <form className="inline-form" onSubmit={handleAddActionItem}>
          <label>
            Description
            <input value={description} onChange={(e) => setDescription(e.target.value)} required />
          </label>
          <label>
            Assignee
            <input value={assignee} onChange={(e) => setAssignee(e.target.value)} placeholder="optional" />
          </label>
          <button type="submit" disabled={addingItem}>Add action item</button>
        </form>
      </div>
    </div>
  );
}
