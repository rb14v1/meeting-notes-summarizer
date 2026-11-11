export type UserRole = "member" | "admin";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  date_joined: string;
}

export interface UserBrief {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface ActionItem {
  id: number;
  meeting: number;
  description: string;
  assignee: string | null;
  is_done: boolean;
  is_ai_generated: boolean;
  created_at: string;
}

export interface MeetingSummary {
  id: number;
  summary: string;
  generated_at: string;
}

export interface Meeting {
  id: number;
  title: string;
  meeting_date: string;
  raw_notes: string;
  created_by: UserBrief;
  created_at: string;
  summary: MeetingSummary | null;
  action_items: ActionItem[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
