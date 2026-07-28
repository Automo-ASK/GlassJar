import Navbar from '../components/Navbar'
import Hero from '../components/Hero'
import Features from '../components/Features'
import UseCases from '../components/UseCases'
import HowItWorks from '../components/HowItWorks'
import Contrast from '../components/Contrast'
import CTA from '../components/CTA'
import Footer from '../components/Footer'

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Navbar />
      <main className="flex-1">
        <Hero />
        <Features />
        <UseCases />
        <HowItWorks />
        <Contrast />
        <CTA />
      </main>
      <Footer />
    </div>
  )
}
