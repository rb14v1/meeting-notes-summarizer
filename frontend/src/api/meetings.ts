import { apiClient } from "./client";
import type { ActionItem, Meeting, Paginated } from "../types";

export interface MeetingInput {
  title: string;
  meeting_date: string;
  raw_notes: string;
}

export interface ActionItemInput {
  description: string;
  assignee?: string | null;
}

export interface ActionItemUpdateInput {
  description?: string;
  assignee?: string | null;
  is_done?: boolean;
}

export function listMeetings() {
  return apiClient.get<Paginated<Meeting>>("/meetings/", { params: { page_size: 100 } });
}

export function getMeeting(id: number) {
  return apiClient.get<Meeting>(`/meetings/${id}/`);
}

export function createMeeting(data: MeetingInput) {
  return apiClient.post<Meeting>("/meetings/", data);
}

export function updateMeeting(id: number, data: MeetingInput) {
  return apiClient.put<Meeting>(`/meetings/${id}/`, data);
}

export function deleteMeeting(id: number) {
  return apiClient.delete(`/meetings/${id}/`);
}

export function summarizeMeeting(id: number) {
  return apiClient.post<Meeting>(`/meetings/${id}/summarize/`);
}

export function addActionItem(meetingId: number, data: ActionItemInput) {
  return apiClient.post<ActionItem>(`/meetings/${meetingId}/action-items/`, data);
}

export function updateActionItem(id: number, data: ActionItemUpdateInput) {
  return apiClient.patch<ActionItem>(`/action-items/${id}/`, data);
}

export function deleteActionItem(id: number) {
  return apiClient.delete(`/action-items/${id}/`);
}
