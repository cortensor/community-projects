import React from "react";
import { Github } from "lucide-react";

import { Navigate } from "react-router-dom";
function Navbar() {
  return (
    <div className="flex items-center justify-between p-5 lg:px-10">
      <div className="font-mali text-white text-3xl tracking-[-0.04em] font-medium">
        Chaplin
      </div>
      <div className="flex gap-3">
        {/* 
          Botão "Discord" (Secundário)
          - A cor de hover foi alterada para bg-neutral-700 (#404040)
          - Isso cria um contraste claro com a borda (#303136)
        */}
        <a
          href="https://discord.com/channels/1174034150462861324/1433186185253093517"
          target="_blank"
          rel="noopener noreferrer"
          className="flex w-25 py-2 px-5 border-[#303136] border rounded-full text-white text-[0.92em] justify-center items-center cursor-pointer transition-all duration-200 active:scale-95 hover:bg-[#1F1F23] select-none"
        >
          Discord
        </a>

        {/* 
          Botão "Docs" (Primário)
          - A cor de hover foi alterada para bg-gray-200 para corresponder
            exatamente ao botão "Continue with MetaMask".
        */}
        <a
  href="https://github.com/lumitylabs/chaplin"
  target="_blank"
  rel="noopener noreferrer"
  className="flex w-30 py-2 px-5 bg-white text-black text-[0.92em] rounded-full justify-center items-center gap-2 cursor-pointer  transition-all active:scale-95 duration-200 hover:bg-[#E3E3E4] select-none"
>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="currentColor"
    className="w-4 h-4"
  >
    <path
      fillRule="evenodd"
      d="M12 .5C5.648.5.5 5.648.5 12a11.5 11.5 0 007.867 10.936c.575.105.784-.25.784-.555 0-.274-.01-1.001-.015-1.964-3.2.696-3.876-1.543-3.876-1.543-.523-1.33-1.278-1.686-1.278-1.686-1.044-.715.08-.7.08-.7 1.153.081 1.76 1.184 1.76 1.184 1.027 1.76 2.695 1.252 3.352.958.104-.744.403-1.252.732-1.54-2.553-.29-5.236-1.277-5.236-5.682 0-1.256.448-2.284 1.183-3.09-.118-.29-.513-1.457.113-3.038 0 0 .967-.31 3.17 1.18a11.04 11.04 0 012.886-.388c.978.005 1.964.132 2.886.388 2.202-1.49 3.167-1.18 3.167-1.18.628 1.58.233 2.747.115 3.038.737.806 1.182 1.834 1.182 3.09 0 4.416-2.688 5.388-5.25 5.672.414.36.784 1.07.784 2.16 0 1.56-.014 2.82-.014 3.205 0 .308.206.666.792.552A11.5 11.5 0 0023.5 12C23.5 5.648 18.352.5 12 .5z"
      clipRule="evenodd"
    />
  </svg>
  GitHub
</a>
      </div>
    </div>
  );
}

export default Navbar;
