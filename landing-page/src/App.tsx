import { CustomCursor } from './components/CustomCursor/CustomCursor';
import { Hero }     from './components/Hero/Hero';
import { Section2 } from './components/Section2/Section2';
import { Section3 } from './components/Section3/Section3';
import { Section4 } from './components/Section4/Section4';
import { Section5 } from './components/Section5/Section5';
import { Footer }   from './components/Footer/Footer';

/**
 * App — Thin composition shell.
 * Add new landing page sections here as named components.
 * No logic, no styles, no inline sx props live here.
 */
export default function App() {
  return (
    <>
      <CustomCursor />
      <Hero />
      <Section2 />
      <Section3 />
      <Section4 />
      <Section5 />
      <Footer />
    </>
  );
}
