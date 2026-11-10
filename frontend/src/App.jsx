import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import Layout from './components/Layout.jsx'
import { Skeleton } from './components/UI.jsx'
import AuthPage from './pages/AuthPage.jsx'
import Overview from './pages/Overview.jsx'
import Assistant from './pages/Assistant.jsx'
import Discover from './pages/Discover.jsx'
import Compare from './pages/Compare.jsx'
import Cart from './pages/Cart.jsx'
import Platforms from './pages/Platforms.jsx'
import Orders from './pages/Orders.jsx'
import Memory from './pages/Memory.jsx'
import Insights from './pages/Insights.jsx'
import Settings from './pages/Settings.jsx'

function Protected({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-10"><Skeleton className="h-40 w-full" /></div>
  return user ? children : <Navigate to="/login" replace />
}

export default function App() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <AuthPage mode="login" />} />
      <Route path="/register" element={user ? <Navigate to="/" replace /> : <AuthPage mode="register" />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/" element={<Overview />} />
        <Route path="/assistant" element={<Assistant />} />
        <Route path="/discover" element={<Discover />} />
        <Route path="/compare" element={<Compare />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/platforms" element={<Platforms />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/memory" element={<Memory />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
