import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Layout from './components/layout/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Tasks from './pages/Tasks'
import Assignments from './pages/Assignments'
import TaskDetail from './pages/TaskDetail'
import ExecuteTask from './pages/ExecuteTask'
import TaskReview from './pages/TaskReview'
import TaskCreationApproval from './pages/TaskCreationApproval'
import PlanApproval from './pages/PlanApproval'
import Cards from './pages/Cards'
import CardDetail from './pages/CardDetail'
import Archive from './pages/Archive'
import Statistics from './pages/Statistics'
import Calendar from './pages/Calendar'
import CreateTask from './pages/CreateTask'
import EditTask from './pages/EditTask'
import CreateCard from './pages/CreateCard'
import Employees from './pages/Employees'
import Delegation from './pages/Delegation'
import Profile from './pages/Profile'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore()

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="tasks" element={<Tasks />} />
          <Route path="assignments" element={<Assignments />} />
          <Route path="tasks/new" element={<CreateTask />} />
          <Route path="tasks/:id" element={<TaskDetail />} />
          <Route path="tasks/:id/edit" element={<EditTask />} />
          <Route path="tasks/:id/execute" element={<ExecuteTask />} />
          <Route path="tasks/:id/review" element={<TaskReview />} />
          <Route path="tasks/:id/creation-approval" element={<TaskCreationApproval />} />
          <Route path="tasks/:id/approve-plan" element={<PlanApproval />} />
          <Route path="calendar" element={<Calendar />} />
          <Route path="cards/:cardId/tasks/new" element={<CreateTask />} />
          <Route path="cards" element={<Cards />} />
          <Route path="cards/new" element={<CreateCard />} />
          <Route path="cards/:id" element={<CardDetail />} />
          <Route path="cards/:cardId/tasks/new" element={<CreateTask />} />
          <Route path="archive" element={<Archive />} />
          <Route path="statistics" element={<Statistics />} />
          <Route path="employees" element={<Employees />} />
          <Route path="delegation" element={<Delegation />} />
          <Route path="profile" element={<Profile />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App

