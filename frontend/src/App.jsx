import React from 'react'
import {BrowserRouter,Routes,Route} from "react-router-dom"
import Home from './pages/Home'
import Navbar from './components/Navbar'
import About from './pages/About'
import Footer from './components/Footer'
import Contact from './pages/Contact'
import Recognition from './pages/Recognition'

const App = () => {
  return (
    <BrowserRouter>
    <Navbar />
      <Routes>
        <Route path="/" element={<Home  />} />
        <Route path="/recognition" element={<Recognition  />} />
        <Route path="/about" element={<About  />} />
        <Route path="/contact" element={<Contact  />} />  
      </Routes>
    <Footer />
    </BrowserRouter>
  )
}

export default App
