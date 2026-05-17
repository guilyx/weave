import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import CampaignDetailPage from "./pages/CampaignDetailPage";
import CampaignListPage from "./pages/CampaignListPage";
import CreateCampaignPage from "./pages/CreateCampaignPage";
import LiveSessionPage from "./pages/LiveSessionPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<CampaignListPage />} />
        <Route path="/campaigns/new" element={<CreateCampaignPage />} />
        <Route path="/campaigns/:campaignId" element={<CampaignDetailPage />} />
        <Route
          path="/campaigns/:campaignId/sessions/:sessionId"
          element={<LiveSessionPage />}
        />
      </Route>
    </Routes>
  );
}
