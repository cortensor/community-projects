"use client";
import { Button } from "@/components/ui/button";
import { useEffect } from "react";
import useWindowWidth from "@/hooks/useWindowWidth"; 
import AgentSidebarMobile from "./AgentSidebarMobile"; 

function AgentSidebarDesktop({ agents, activeAgent, handleAgentClick }) {
  useEffect(() => {
    const style = document.createElement("style");
    style.innerHTML = `
      /* ✨ Efek Gradasi Metalik Abu Putih Bergerak */
      @keyframes gradientShine {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
      }
      .animated-gradient {
        background: linear-gradient(
          270deg,
          #e5e7eb, #d1d5db, #f9fafb, #9ca3af, #e5e7eb
        );
        background-size: 300% 300%;
        animation: gradientShine 3.5s ease-in-out infinite;
        color: #1f2937; 
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
      }
      .animated-gradient:hover {
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15);
        transform: scale(1.05);
      }
    `;
    document.head.appendChild(style);
    return () => style.remove();
  }, []);

  return (
    <aside className="w-64 bg-transparent p-4 flex flex-col gap-3">
      {agents.map((agent) => {
        const isActive = activeAgent === agent;
        return (
          <Button
            key={agent}
            onClick={() => handleAgentClick(agent)}
            className={`w-full rounded-lg border font-medium transition-all duration-300 relative overflow-hidden ${
              isActive
                ? "animated-gradient text-gray-900 scale-[1.05] border-gray-400 shadow-md"
                : "bg-white text-gray-800 border-gray-200 hover:bg-gray-50"
            }`}
            variant="ghost"
          >
            {agent}
          </Button>
        );
      })}
    </aside>
  );
}


export default function AgentSidebar(props) {
  const width = useWindowWidth();
  const isMobile = width < 1024; 

  if (isMobile) {
    return <AgentSidebarMobile {...props} />;
  }
  return <AgentSidebarDesktop {...props} />;
}