// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar  from './components/Sidebar'
import Upload   from './pages/Upload'
import Report   from './pages/Report'
import History  from './pages/History'

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <Routes>
          <Route path="/"            element={<Upload />} />
          <Route path="/report/:id"  element={<Report />} />
          <Route path="/history"     element={<History />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
