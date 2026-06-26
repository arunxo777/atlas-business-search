import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { Home } from "@/pages/Home";
import { Results } from "@/pages/Results";

function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/results/:jobId" element={<Results />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}

export default App;
