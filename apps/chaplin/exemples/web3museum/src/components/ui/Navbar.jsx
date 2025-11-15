import React from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronsLeft,
  Server,
  Wrench,
  Braces,
  Palette,
  LoaderCircle,
  ChevronDown
} from "lucide-react";
import SimpleBar from 'simplebar-react';

const ProgressStep = ({ step }) => {
  const isCompleted = step.status === 'completed' || step.status === 'generated';
  const isProcessing = step.status === 'processing';
  const hasContent = !!step.content;

  const isExpandable = isCompleted && hasContent &&
    (step.type === 'integrator' || step.type !== 'image' &&  step.type !== 'connection' &&
      (typeof step.content === 'string' && step.content.length > 1));

  const backgroundColor = (step.type === 'agent' || step.type === 'integrator') ? 'bg-black' : 'bg-[#18181B]';
  const processingRing = isProcessing ? 'ring-2 ring-offset-2 ring-offset-[#131316] ring-white/80' : '';
  const pulseClass = isProcessing ? 'animate-pulse' : '';

  const outputTextStyle = "font-mono text-xs text-[#A2A2AB] whitespace-pre-wrap break-words";

  const getStepIcon = () => {
    switch (step.type) {
      case 'connection': return <Server size={20} className="text-gray-300" />;
      case 'agent': return <Wrench size={20} className="text-gray-300" />;
      case 'integrator': return <Braces size={20} className="text-gray-300" />;
      case 'image': return <Palette size={20} className="text-gray-300" />;
      default: return null;
    }
  };


  const StepHeader = () => {

    const getStatusLineText = () => {
      if (isProcessing) {

        if (typeof step.content === 'string') {
          return step.content;
        }

        return 'Processing...';
      }
      return step.status.charAt(0).toUpperCase() + step.status.slice(1);
    };

    return (
      <div className="flex items-center justify-between p-3">
        <div className="flex items-center gap-4 min-w-0">
          <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-r from-[#0A0A0A] to-[#2B2B2B] flex-shrink-0">
            {getStepIcon()}
          </div>
          <div className="flex flex-col min-w-0">
            <span className="font-medium text-sm text-white truncate">{step.name}</span>
            <span className="text-xs text-gray-400 truncate">{getStatusLineText()}</span>
          </div>
        </div>
        <div className="w-6 h-6 flex items-center justify-center flex-shrink-0 ml-2">
          {isProcessing && <LoaderCircle size={20} className="animate-spin text-gray-400" />}
          {isExpandable && <ChevronDown size={20} className="text-gray-500 transition-transform duration-300 group-open:rotate-180" />}
        </div>
      </div>
    );
  };

  if (isExpandable) {
    return (
      <details className={`${backgroundColor} ${processingRing} ${pulseClass} rounded-lg group transition-all duration-300`}>
        <summary className="list-none cursor-pointer">
          <StepHeader />
        </summary>
        <div className="p-4 pt-2 border-t border-[#26272B]">
          {typeof step.content === 'string' ? (
            <p className={outputTextStyle}>{step.content}</p>
          ) : (
            <pre className={outputTextStyle}>
              <code>{JSON.stringify(step.content, null, 2)}</code>
            </pre>
          )}
        </div>
      </details>
    );
  }

  return (
    <div className={`${backgroundColor} ${processingRing} ${pulseClass} rounded-lg transition-all duration-300`}>
      <StepHeader />
    </div>
  );
};



function NavbarHeader({ closeNavbar }) {
  const navigate = useNavigate();
  return (
    <div className="flex items-center justify-between px-5 pr-2 pt-5 pb-4 flex-shrink-0">
      <div className="font-inter w-min font-medium text-md text-white tracking-[-0.04em] cursor-pointer" onClick={() => navigate("/")}>
        Workgroup
      </div>
      <button onClick={closeNavbar} className="flex items-center justify-center w-9 h-9 rounded-full hover:bg-[#1F1F22] transition duration-200 cursor-pointer">
        <ChevronsLeft color="#86868E" size={17} />
      </button>
    </div>
  );
}

function Navbar({ isOpen, setIsOpen, progressSteps }) {
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
        className="fixed top-0 left-0 w-[340px] h-screen bg-[#131316] border-r-[1px] border-[#26272B] font-inter flex flex-col z-40"
      >
        <NavbarHeader closeNavbar={() => setIsOpen(false)} />

        <div className="flex-grow overflow-hidden">
          {progressSteps && progressSteps.length > 0 ? (
            <SimpleBar style={{ maxHeight: 'calc(100vh - 80px)' }} className="chaplin-sidebar-scrollbar">
              <div className="flex flex-col gap-3 p-5">
                {progressSteps.map((step) => (
                  <ProgressStep key={step.id} step={step} />
                ))}
              </div>
            </SimpleBar>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Wrench size={45} strokeWidth={1} color="#1B1B1B" className="mb-2" />
              <p className="font-mono text-sm text-[#414141] leading-tight tracking-tight">
                Your workgroup will<br />appear here
              </p>
            </div>
          )}
        </div>
      </motion.nav>
    </>
  );
}

export default Navbar;