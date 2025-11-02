import React, { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom"; // Importar useLocation
import { motion, AnimatePresence } from "framer-motion";
import { Plus, LogOut, Star, ChevronDown, ChevronsLeft } from 'lucide-react';
import hatIcon from "../../../assets/hatIcon.svg";
import Avatar from "../../../assets/avatar.png";
import Persona from "../../../assets/persona.png";
import SimpleBar from "simplebar-react";
import "simplebar-react/dist/simplebar.min.css";
import { SignOutButton, useUser } from "@clerk/clerk-react";

// --- SUB-COMPONENTES DA NAVBAR ---

function NavbarHeader({ closeNavbar, handleMobileNavClick }) {
  const navigate = useNavigate();

  const handleCreateClick = () => {
    navigate("/create");
    handleMobileNavClick();
  };

  return (
    <div className="flex flex-col gap-6 px-5 pr-2 pt-5 pb-0 ">
      <div className="flex items-center justify-between">
        <div className="font-mali w-min font-medium text-2xl text-white tracking-[-0.04em] cursor-pointer" onClick={() => navigate("/home")}>
          Chaplin
        </div>
        <button onClick={closeNavbar} className="flex items-center justify-center w-9 h-9 rounded-full hover:bg-[#1F1F22] transition duration-200 cursor-pointer">
          <ChevronsLeft color="#86868E" size={17} />
        </button>
      </div>
      <button onClick={handleCreateClick} className="flex p-1.5 px-3 gap-1 bg-[#202024] w-32 items-center rounded-full text-[#FAFAFA] text-[0.84em] border-[1px] border-[#26272B] cursor-pointer hover:bg-[#3B3B41] transition-all active:scale-95 duration-200">
        <Plus color="#94949C" height={36} width={36} strokeWidth={1.5}/>
        Create
      </button>
    </div>
  );
}

function PersonaPage({ viewMode, handleMobileNavClick }) {
  const navigate = useNavigate();
  const location = useLocation(); // Hook para obter a localização atual
  const isHomePage = location.pathname === '/home'; // Verifica se estamos na página Home

  const baseButtonClasses = "flex items-center gap-3 p-3.5 text-[0.84em] rounded-lg transition-all duration-200 active:scale-95 cursor-pointer w-full";
  const activeClasses = "bg-[#26272B] text-white font-semibold";
  const inactiveClasses = "text-white hover:bg-[#1F1F22] font-normal";

  const handleNavigation = (targetView) => {
    // Navega para a home E passa o view mode desejado no estado da navegação
    navigate("/home", { state: { desiredView: targetView } });
    handleMobileNavClick();
  };

  return (
    <div className="flex flex-col gap-2 font-semibold text-[#817676] px-5">
      {/* A classe ativa só é aplicada se estivermos na home E o viewMode corresponder */}
      <button className={`${baseButtonClasses} ${isHomePage && viewMode === 'all' ? activeClasses : inactiveClasses}`} onClick={() => handleNavigation('all')}>
        <img className="w-5" src={hatIcon} alt="All Chaplins" />
        Chaplins
      </button>
      <button className={`${baseButtonClasses} ${isHomePage && viewMode === 'favorites' ? activeClasses : inactiveClasses}`} onClick={() => handleNavigation('favorites')}>
        <Star fill="white" color="white" size={20} />
        Favorites
      </button>
    </div>
  );
}

function PersonaItem({ name, image }) {
  return (
    <button className="flex items-center gap-2 hover:bg-[#262628] rounded-lg cursor-pointer w-full">
      <div className="flex px-2.5 py-1.5 items-center gap-2">
        <img className="w-9 h-9 rounded-full" src={image} alt={name} />
        <div className="font-inter text-[1.06em] text-[#FAF6F3]">{name}</div>
      </div>
    </button>
  );
}

function YourPersonas() {
  return (
    <div className="flex h-full text-[0.80em] text-[#9898A0] flex-col gap-2 px-5">
      Your Chaplins
      <SimpleBar style={{ maxHeight: "32.5rem", minHeight: "15rem" }} autoHide={false}>
        <div className="flex max-h-full flex-col gap-3">
          <PersonaItem name="Orc" image={Persona} />
          <PersonaItem name="Miner" image={Persona} />
        </div>
      </SimpleBar>
    </div>
  );
}

function UserAccount() {
  const [isOpen, setIsOpen] = useState(false);
  const { user } = useUser();
  const dropdownRef = useRef(null);
  const buttonRef = useRef(null);

  const formatWalletAddress = (address, startChars = 7, endChars = 4) => {
    if (!address || address.length <= startChars + endChars) return address;
    return `${address.slice(0, startChars)}...${address.slice(-endChars)}`;
  };

  const walletAddress = user?.web3Wallets?.[0]?.web3Wallet;
  const displayText = walletAddress ? formatWalletAddress(walletAddress) : '1A1zP1e...22e';

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        dropdownRef.current && !dropdownRef.current.contains(event.target) &&
        buttonRef.current && !buttonRef.current.contains(event.target)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  return (
    <div className="px-5 mt-4 mb-4">
      <div className="flex items-center border-t-[1px] border-[#26272B] relative">
        <button
          ref={buttonRef}
          onClick={() => setIsOpen(!isOpen)}
          className="flex mt-3 px-2 py-1.5 w-full items-center gap-3 hover:bg-[#3F3F46] rounded-lg cursor-pointer"
        >
          <img className="w-9 h-9 rounded-full shadow-xl" src={user?.imageUrl || Avatar} alt="User Avatar" />
          <div className="flex w-full items-center px-1 justify-between">
            <span className="font-inter text-[#F4F1F4] font-light text-[0.78em] truncate">
              {displayText}
            </span>
            <ChevronDown size={16} color="#A2A2AB" />
          </div>
        </button>
        {isOpen && (
          <div
            ref={dropdownRef}
            className="absolute bottom-14 left-0 w-full bg-[#202024] rounded-lg shadow-lg overflow-hidden z-10"
          >
            <SignOutButton>
              <button className="flex w-full items-center justify-between gap-3 px-4 py-3 hover:bg-[#3F3F46] text-[#EDEFF1] font-inter text-sm cursor-pointer">
                <span>Logout</span>
                <LogOut size={18} />
              </button>
            </SignOutButton>
          </div>
        )}
      </div>
    </div>
  );
}

// --- COMPONENTE PRINCIPAL DA NAVBAR ---

function PersonaNavbar({ isOpen, setIsOpen, viewMode, setViewMode, handleMobileNavClick }) {
  const variants = {
    open: { x: 0 },
    closed: { x: "-100%" },
  };

  return (
    <>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="fixed inset-0 bg-black/60 z-30 lg:hidden"
          />
        )}
      </AnimatePresence>

      <motion.nav
        initial="closed"
        animate={isOpen ? "open" : "closed"}
        variants={variants}
        transition={{ type: "spring", stiffness: 400, damping: 40 }}
        className="fixed top-0 left-0 w-[260px] h-screen bg-[#131316] border-r-[1px] border-[#26272B] font-inter flex flex-col justify-between z-40 select-none"
      >
        <div className="flex flex-col gap-8 h-full">
          <div className="flex flex-col gap-5">
            <NavbarHeader closeNavbar={() => setIsOpen(false)} handleMobileNavClick={handleMobileNavClick} />
            <PersonaPage viewMode={viewMode} handleMobileNavClick={handleMobileNavClick} />
          </div>
          <div className="flex flex-col">
            <YourPersonas />
          </div>
        </div>
        <UserAccount />
      </motion.nav>
    </>
  );
}

export default PersonaNavbar;