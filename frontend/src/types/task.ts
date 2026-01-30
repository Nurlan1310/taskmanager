export interface Employee {
  id: number
  user: {
    id: number
    username: string
    email: string
    first_name: string
    last_name: string
  }
  firstname?: string
  lastname?: string
  middlename?: string
  full_name?: string
  full_name_complete?: string
  position?: string
  department?: {
    id: number
    name: string
    priority?: number
  }
  role?: string
  photo_url?: string
  internal_phone?: string
  external_phone?: string
}

export interface Task {
  id: number
  title: string
  description: string
  status: 'new' | 'in_progress' | 'done' | 'under_review' | 'sent_for_review' | 'rejected' | 'pending' | 'revision' | 'send_for_approve'
  status_display?: string
  task_type: 'regular' | 'approval' | 'review' | 'task_approval'
  task_type_display?: string
  priority?: 'low' | 'normal' | 'high' | 'urgent'
  priority_display?: string
  created_at: string
  due_date?: string
  completed_at?: string
  created_by: Employee
  assigned_employee?: Employee
  assigned_department?: {
    id: number
    name: string
    priority?: number
  }
  recipients: Employee[]
  card?: number
  card_title?: string
  attachment?: string
  google_drive_link?: string
  review_comment?: string
  history?: TaskHistory[]
  attachments?: TaskAttachment[]
  redirected_by?: Employee
  redirect_chain?: number[]
  redirect_chain_employees?: Employee[]
  current_reviewer?: Employee
  current_approver?: Employee
  is_according_to_plan?: boolean
  creation_approval_chain?: number[]
  current_approval_index?: number | null
  parent_task?: number
  relation_type?: 'creation_approval' | 'execution_review'
}

export interface TaskAttachment {
  id: number
  file?: string
  file_name?: string
  link?: string
  uploaded_by?: Employee
  uploaded_at?: string
}

export interface TaskHistory {
  id: number
  action: string
  action_display?: string
  employee?: Employee
  comment?: string
  timestamp: string
}

export type TaskStatus = Task['status']
export type TaskType = Task['task_type']
export type TaskPriority = Task['priority']

// Добавьте в конец файла frontend/src/types/task.ts

export interface EventCard {
  id: number
  title: string
  description?: string
  start_date: string
  end_date?: string
  created_by: {
    user: {
      first_name: string
      last_name: string
    }
  }
  responsible_department?: {
    id: number
    name: string
    priority?: number
  }
  progress: number
  approval_count: number
  urgent_count: number
  other_count: number
  done_count: number
  user_active_count?: number
  user_urgent_count?: number
  user_approval_count?: number
  user_total_tasks?: number
  user_done_tasks?: number
  categories: Array<{ id: number; name: string; slug: string }>
  has_plan?: boolean
  plan_status?: 'draft' | 'pending' | 'rejected' | 'approved'
  visible?: boolean
  is_active?: boolean
  approvers?: any[]
  current_approver_index?: number
  final_approver?: {
    id: number
    user: {
      first_name: string
      last_name: string
    }
  }  
  plan_file?: string
  plan_rejected_reason?: string
  
}

export interface Notification {
  id: number
  message: string
  url?: string
  type?: string
  task_id?: number
  created_at: string
  is_read: boolean
}