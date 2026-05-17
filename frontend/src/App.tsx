import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Courses from "./pages/Courses";
import CourseDetail from "./pages/CourseDetail";
import CreateCourse from "./pages/CreateCourse";
import BrowseCourses from "./pages/BrowseCourses";
import AnnouncementsHub from "./pages/AnnouncementsHub";
import CourseAnnouncements from "./pages/CourseAnnouncements";
import StudentExams from "./pages/StudentExams";
import ProfessorExams from "./pages/ProfessorExams";
import CreateExam from "./pages/CreateExam";
import ProfessorSubmissions from "./pages/ProfessorSubmissions";
import SubmissionDetail from "./pages/SubmissionDetail";
import SubmitExam from "./pages/SubmitExam";
import TakeExam from "./pages/TakeExam";
import MyResults from "./pages/MyResults";
import Analytics from "./pages/Analytics";
import NotFound from "./pages/NotFound";
import { DashboardLayout } from "./components/layout/DashboardLayout";
import Profile from "./pages/Profile";
import Settings from "./pages/Settings";
import { UserSettingsProvider } from "./contexts/UserSettingsContext";
import { ThemeProvider } from "next-themes";
import { Loader2 } from "lucide-react";
import { DueRemindersAlert } from "@/components/layout/DueRemindersAlert";

const queryClient = new QueryClient();

function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode; allowedRoles?: string[] }) {
  const { isAuthenticated, user, isLoading } = useAuth();
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return <DashboardLayout>{children}</DashboardLayout>;
}

function AppRoutes() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Login />} />
      <Route path="/" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />} />
      
      {/* Protected Routes */}
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route
        path="/analytics"
        element={
          <ProtectedRoute allowedRoles={['professor', 'student', 'admin']}>
            <Analytics />
          </ProtectedRoute>
        }
      />
      <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
      <Route
        path="/announcements"
        element={
          <ProtectedRoute allowedRoles={['professor', 'student', 'admin']}>
            <AnnouncementsHub />
          </ProtectedRoute>
        }
      />
      <Route
        path="/courses/:courseId/announcements"
        element={
          <ProtectedRoute allowedRoles={['professor', 'student', 'admin']}>
            <CourseAnnouncements />
          </ProtectedRoute>
        }
      />
      
      {/* Professor Routes */}
      <Route path="/courses" element={<ProtectedRoute allowedRoles={['professor', 'admin']}><Courses /></ProtectedRoute>} />
      <Route path="/courses/new" element={<ProtectedRoute allowedRoles={['professor', 'admin']}><CreateCourse /></ProtectedRoute>} />
      <Route path="/courses/:courseId" element={<ProtectedRoute allowedRoles={['professor', 'admin']}><CourseDetail /></ProtectedRoute>} />
      <Route path="/exams" element={<ProtectedRoute allowedRoles={['professor', 'admin']}><ProfessorExams /></ProtectedRoute>} />
      <Route path="/exams/new" element={<ProtectedRoute allowedRoles={['professor', 'admin']}><CreateExam /></ProtectedRoute>} />
      <Route path="/exams/:id/edit" element={<ProtectedRoute allowedRoles={['professor', 'admin']}><CreateExam /></ProtectedRoute>} />
      <Route path="/submissions" element={<ProtectedRoute allowedRoles={['professor', 'admin']}><ProfessorSubmissions /></ProtectedRoute>} />
      <Route path="/submissions/:id" element={<ProtectedRoute><SubmissionDetail /></ProtectedRoute>} />
      
      {/* Student Routes */}
      <Route path="/browse-courses" element={<ProtectedRoute allowedRoles={['student']}><BrowseCourses /></ProtectedRoute>} />
      <Route path="/my-exams" element={<ProtectedRoute allowedRoles={['student']}><StudentExams /></ProtectedRoute>} />
      <Route path="/take-exam/:examId" element={<ProtectedRoute allowedRoles={['student']}><TakeExam /></ProtectedRoute>} />
      <Route path="/submit-exam/:id" element={<ProtectedRoute allowedRoles={['student']}><SubmitExam /></ProtectedRoute>} />
      <Route path="/my-results" element={<ProtectedRoute allowedRoles={['student']}><MyResults /></ProtectedRoute>} />
      
      {/* Catch-all */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem storageKey="mathgrade-ui-theme">
        <UserSettingsProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <BrowserRouter>
              <DueRemindersAlert />
              <AppRoutes />
            </BrowserRouter>
          </TooltipProvider>
        </UserSettingsProvider>
      </ThemeProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;