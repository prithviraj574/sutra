import { Navigate, Route, Routes, useParams } from "react-router-dom";

import { ChatPage } from "../features/chat/ChatPage";
import { HubPage } from "../features/hub/HubPage";
import { SecretsPage } from "../features/secrets/SecretsPage";

function ChatRoute() {
  const params = useParams();
  if (!params.agentId) {
    return <Navigate replace to="/" />;
  }
  return <ChatPage agentId={params.agentId} />;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<HubPage />} />
      <Route path="/agents/:agentId" element={<ChatRoute />} />
      <Route path="/secrets" element={<SecretsPage />} />
    </Routes>
  );
}
