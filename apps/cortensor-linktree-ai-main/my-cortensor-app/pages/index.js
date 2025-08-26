import React, { useState } from "react";
import CompanyLinktree from "../src/components/CompanyLinktree";
import AskCortensorAI from "../src/components/AskCortensorAI";

export default function Home() {
  const [menuActive, setMenuActive] = useState(false);

  return (
    <div>
      <CompanyLinktree onMenuStateChange={setMenuActive} />
      {!menuActive && <AskCortensorAI />}
    </div>
  );
}
