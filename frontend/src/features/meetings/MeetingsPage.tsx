import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { extractErrorMessage } from "../../api/client";
import { createMeeting, deleteMeeting, listMeetings } from "../../api/meetings";
import { useAuth } from "../../auth/AuthContext";
import type { Meeting } from "../../types";
import { today } from "../../utils/format";

export function MeetingsPage() {
  const { user } = useAuth();
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState(today());
  const [rawNotes, setRawNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await listMeetings();
      setMeetings(res.data.results);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function resetForm() {
    setTitle("");
    setMeetingDate(today());
    setRawNotes("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createMeeting({ title, meeting_date: meetingDate, raw_notes: rawNotes });
      resetForm();
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  function canModify(meeting: Meeting): boolean {
    return !!user && (user.id === meeting.created_by.id || user.role === "admin");
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this meeting?")) return;
    setError(null);
    try {
      await deleteMeeting(id);
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Meetings</h1>
      </div>

      <div className="card">
        <h2>New meeting</h2>
        <form className="form-row" onSubmit={handleSubmit}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Date
            <input type="date" value={meetingDate} onChange={(e) => setMeetingDate(e.target.value)} required />
          </label>
          <label style={{ flexBasis: "100%" }}>
            Raw notes
            <textarea
              rows={4}
              value={rawNotes}
              onChange={(e) => setRawNotes(e.target.value)}
              placeholder="Paste or type the freeform meeting notes here..."
              required
            />
          </label>
          <button type="submit" disabled={submitting}>Create meeting</button>
        </form>
        {error && <div className="form-error">{error}</div>}
      </div>

      <div className="card">
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Date</th>
                <th>Created by</th>
                <th>Summary</th>
                <th>Action items</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {meetings.map((m) => (
                <tr key={m.id}>
                  <td><Link to={`/meetings/${m.id}`}>{m.title}</Link></td>
                  <td>{m.meeting_date}</td>
                  <td>{m.created_by.full_name || m.created_by.email}</td>
                  <td>{m.summary ? "Yes" : <span className="muted">Not yet</span>}</td>
                  <td>{m.action_items.length}</td>
                  <td className="actions">
                    {canModify(m) && (
                      <button className="danger" onClick={() => handleDelete(m.id)}>Delete</button>
                    )}
                  </td>
                </tr>
              ))}
              {meetings.length === 0 && (
                <tr><td colSpan={6} className="muted">No meetings yet.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
