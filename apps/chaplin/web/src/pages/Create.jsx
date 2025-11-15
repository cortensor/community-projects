import React, { useRef, useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Menu, WandSparkles, Globe, ChevronDown, Plus, Trash2, PenLine, Play, Loader2, TextSearch, SquareCode, LockKeyholeOpen, Pencil } from "lucide-react";
import SimpleBar from 'simplebar-react';
import 'simplebar-react/dist/simplebar.min.css';

// Componentes e Assets
import PersonaNavbar from "../components/ui/general/PersonaNavbar";
import Persona from "../assets/persona.png";
import ExpandableInput from "../components/ui/create/ExpandableInput";
import { generateWorkgroup, generateImage, runAgent, createChaplin } from "../services/apiService";
import SpecialistSkeleton from "../components/ui/create/SpecialistSkeleton";
import CreateModal from "../components/ui/create/CreateModal";
import TryModal from "../components/ui/general/TryModal";

/* ------------------ Constantes ------------------ */
const NAME_MAX = 25;
const INSTR_MAX = 500;
const STEP2_KEY_MAX = 25;
const STEP2_DESC_MAX = 100;
const PROMPT_SPECIALIST_MAX = 4000;
const MAX_STEP2_GROUPS = 6;
const SPECIALIST_NAME_MAX = 60;
const CATEGORY_OPTIONS = [
  "Assistants", "Anime", "Creativity & Writing", "Entertainment & Gaming",
  "History", "Humor", "Learning",
];


/* ------------------ Subcomponentes ------------------ */
function Specialist({
  name,
  prompt,
  response,
  isRunning,
  onRun,
  onOpenModal,
  onOpenResponseModal,
  onPromptChange,
  onNameChange
}) {
  const hasResponse = !!response;
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(name);
  const editRef = useRef(null);

  useEffect(() => {
    setEditedName(name);
  }, [name]);

  const handleSaveName = useCallback(() => {
    if (editedName.trim() && editedName !== name) {
      onNameChange(editedName.trim());
    } else {
      setEditedName(name);
    }
    setIsEditingName(false);
  }, [editedName, name, onNameChange]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (editRef.current && !editRef.current.contains(event.target)) {
        handleSaveName();
      }
    }
    if (isEditingName) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isEditingName, handleSaveName]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSaveName();
    } else if (e.key === 'Escape') {
      setEditedName(name);
      setIsEditingName(false);
    }
  };

  const toggleEditMode = () => {
    if (isEditingName) {
      handleSaveName();
    } else {
      setIsEditingName(true);
    }
  };

  return (
    <div className="w-full border border-[#3A3A3A] rounded-xl font-inter text-sm flex flex-col justify-between">
      <div className="flex flex-col gap-3 p-4">
        <div className="flex justify-between items-center">
          <div className="flex flex-row gap-2 items-center flex-grow pr-2 min-w-0">
            {isEditingName ? (
              <div ref={editRef} className="w-full">
                <input
                  type="text"
                  value={editedName}
                  onChange={(e) => setEditedName(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-transparent border border-[#3A3A3A] text-white font-semibold outline-none rounded-lg px-2 py-1 focus:ring-1 focus:ring-[#FAFAFA]"
                  maxLength={SPECIALIST_NAME_MAX}
                  autoFocus
                />
              </div>
            ) : (
              <div className="font-semibold text-white truncate" title={name}>{name}</div>
            )}
          </div>
          <div className="flex justify-start items-start flex-shrink-0">
            <button onClick={toggleEditMode} className="p-2 rounded-full hover:bg-[#2C2C30] transition duration-200 active:scale-95 cursor-pointer">
              <Pencil alt="Edit Name Agent" size={16} color="#9E9EA0" />
            </button>
            <button className="p-2 rounded-full hover:bg-[#2C2C30] transition duration-200 active:scale-95 cursor-pointer">
              <LockKeyholeOpen alt="Open/Lock Agent" size={16} color="#9E9EA0" />
            </button>
            <button
              onClick={onRun}
              disabled={isRunning}
              className="p-2 rounded-full hover:bg-[#2C2C30] transition duration-200 active:scale-95 cursor-pointer disabled:cursor-not-allowed disabled:hover:bg-transparent"
            >
              {isRunning ? (
                <Loader2 color="#EFEFEF" size={16} className="animate-spin" />
              ) : (
                <Play alt="Run Agent" size={16} color="#9E9EA0" />
              )}
            </button>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <label className="text-[#83828B] text-xs">Prompt</label>
          <ExpandableInput
            value={prompt}
            onChange={onPromptChange}
            placeholder="Specialist Prompt"
            onOpenModal={onOpenModal}
          />
        </div>
      </div>
      <button
        onClick={hasResponse ? onOpenResponseModal : undefined}
        disabled={!hasResponse}
        className={`w-full h-10 rounded-b-[10px] flex items-center justify-end gap-3 px-4 transition-colors duration-200 ${hasResponse
          ? "bg-[#3B3B42] text-[#D9D9D9] font-semibold cursor-pointer hover:bg-[#4a4a52]"
          : "bg-[#202024] text-[#797A86] cursor-default"
          }`}
      >
        <span>Response</span>
        <TextSearch size={16} />
      </button>
    </div>
  );
}

function WorkGroup({
  workgroupData,
  workgroupResponses,
  runningAgentIndex,
  onRunAgent,
  onOpenSpecialistModal,
  onOpenResponseModal,
  isGenerating,
  onPromptChange,
  onNameChange,
}) {
  return (
    <div>
      <div className="flex flex-col gap-6">
        {isGenerating ? (
          <><SpecialistSkeleton /><SpecialistSkeleton /><SpecialistSkeleton /></>
        ) : workgroupData && workgroupData.length > 0 ? (
          workgroupData.map((specialist, index) => (
            <Specialist
              key={index}
              name={specialist.name}
              prompt={specialist.prompt}
              response={workgroupResponses[specialist.name]}
              isRunning={runningAgentIndex === index}
              onRun={() => onRunAgent(index, specialist.name)}
              onOpenModal={() => onOpenSpecialistModal(index)}
              onOpenResponseModal={() => onOpenResponseModal(index)}
              onPromptChange={(e) => onPromptChange(index, e.target.value)}
              onNameChange={(newName) => onNameChange(index, newName)}
            />
          ))
        ) : (
          <div className="text-center py-10 text-[#797A86] text-sm font-regular leading-none">
            <p>Your <span className="font-bold">AI specialists</span> will appear here.</p>
            <p className="mt-1">Click "AI Generate" to create them.</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------ Componente Principal Create ------------------ */
function Create() {
  const [formData, setFormData] = useState({
    name: "",
    category: "",
    instructions: "",
    personaDescription: "",
    avatarUrl: Persona,
    step2: { groups: [{ key: "speech", description: "Character's response to message" }] },
    workgroup: [],
    io: { input: "", output: "Waiting for input..." },
  });

  const [isPublishing, setIsPublishing] = useState(false);
  const navigate = useNavigate();
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGeneratingAvatar, setIsGeneratingAvatar] = useState(false);
  const [runningAgentIndex, setRunningAgentIndex] = useState(null);
  const [workgroupResponses, setWorkgroupResponses] = useState({});
  const [apiError, setApiError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingField, setEditingField] = useState(null);
  const [isNavbarOpen, setIsNavbarOpen] = useState(false);
  const [viewMode, setViewMode] = useState(null);
  const [isAvatarMenuOpen, setIsAvatarMenuOpen] = useState(false);
  const avatarButtonRef = useRef(null);
  const avatarMenuRef = useRef(null);
  const [isCategoryOpen, setIsCategoryOpen] = useState(false);
  const categoryRef = useRef(null);
  const categoryMenuRef = useRef(null);
  const [isTryModalOpen, setIsTryModalOpen] = useState(false);
  const [tryModalChaplin, setTryModalChaplin] = useState(null);

  const getMissingFields = useCallback(() => {
    const missing = [];
    if (formData.name.trim() === "") missing.push("Name");
    if (formData.category.trim() === "") missing.push("Category");
    if (formData.instructions.trim() === "") missing.push("Instructions");
    if (formData.personaDescription.trim() === "") missing.push("Chaplin Description (Step 1)");
    if (formData.workgroup.length === 0) missing.push("Workgroup (Step 3)");
    return missing;
  }, [formData]);

  const missingFields = getMissingFields();
  const isPublishable = missingFields.length === 0;

  const tooltipMessage = (
    <div className="text-sm">
      <span className="font-semibold text-xs text-[#FAFAFA]">Missing required fields:</span>
      <ul className="list-disc list-inside text-xs text-left text-[#D0D0D0] mt-2 space-y-1">
        {missingFields.map(field => (
          <li key={field}>{field}</li>
        ))}
      </ul>
    </div>
  );

  useEffect(() => {
    const isDesktop = window.innerWidth >= 1024;
    setIsNavbarOpen(isDesktop);
  }, []);

  useEffect(() => {
    function handleDocClick(e) {
      if (isAvatarMenuOpen && avatarMenuRef.current && !avatarMenuRef.current.contains(e.target) && avatarButtonRef.current && !avatarButtonRef.current.contains(e.target)) {
        setIsAvatarMenuOpen(false);
      }
      if (isCategoryOpen && categoryMenuRef.current && !categoryMenuRef.current.contains(e.target) && categoryRef.current && !categoryRef.current.contains(e.target)) {
        setIsCategoryOpen(false);
      }
    }
    window.addEventListener("pointerdown", handleDocClick);
    return () => window.removeEventListener("pointerdown", handleDocClick);
  }, [isAvatarMenuOpen, isCategoryOpen]);

  const handlePublish = async () => {
    if (!isPublishable) {
      alert("Please fill all required fields before publishing.");
      return;
    }
    setIsPublishing(true);
    setApiError(null);
    const responseformat = formData.step2.groups.reduce((acc, group) => {
      if (group.key && group.key.trim() !== "") acc[group.key.trim()] = group.description;
      return acc;
    }, {});
    const chaplinData = {
      name: formData.name,
      category: formData.category,
      instructions: formData.instructions,
      description: formData.personaDescription,
      imagebase64: formData.avatarUrl === Persona ? null : formData.avatarUrl,
      workgroup: formData.workgroup,
      responseformat: Object.keys(responseformat).length > 0 ? responseformat : { speech: "character's response to message" },
    };
    const result = await createChaplin(chaplinData);
    if (result.error) {
      console.error("Publishing failed:", result.error);
      setApiError(`Failed to publish: ${result.error}`);
      alert(`Error: Could not publish the Chaplin. ${result.error}`);
    } else {
      alert("Chaplin published successfully!");
      navigate("/");
    }
    setIsPublishing(false);
  };

  const handleGenerateWorkgroup = async () => {
    if (!formData.name || !formData.category || !formData.instructions || !formData.personaDescription) {
      alert("Please fill in Name, Category, Description and Instructions before generating.");
      return;
    }
    const responseFormatObject = formData.step2.groups.reduce((acc, group) => {
      if (group.key && group.key.trim() !== "") {
        acc[group.key.trim()] = group.description;
      }
      return acc;
    }, {});
    let finalResponseFormat = responseFormatObject;
    if (Object.keys(responseFormatObject).length === 0) {
      finalResponseFormat = { speech: "character's response to message" };
    }
    setIsGenerating(true);
    setApiError(null);
    const result = await generateWorkgroup({
      name: formData.name,
      category: formData.category,
      description: formData.personaDescription,
      instructions: formData.instructions,
      responseformat: finalResponseFormat,
    });
    if (result.error) {
      console.error(result.error);
      setApiError(`Failed to generate: ${result.error}`);
      setFormData((prev) => ({ ...prev, workgroup: [] }));
    } else {
      setFormData((prev) => ({ ...prev, workgroup: result.data }));
      setWorkgroupResponses({});
    }
    setIsGenerating(false);
  };

  const handleGenerateImage = async () => {
    if (!formData.name || !formData.category || !formData.personaDescription || !formData.instructions) {
      alert("Please fill in Name, Category, Instructions and Description to generate an image.");
      return;
    }
    setIsGeneratingAvatar(true);
    setIsAvatarMenuOpen(false);
    setApiError(null);
    const result = await generateImage({
      name: formData.name,
      category: formData.category,
      description: formData.personaDescription,
      instructions: formData.instructions
    });
    if (result.error) {
      console.error(result.error);
      setApiError(`Failed to generate image: ${result.error}`);
    } else {
      setFormData(prev => ({ ...prev, avatarUrl: result.data.base64 }));
    }
    setIsGeneratingAvatar(false);
  };

  const handleRunAgent = async (index, agentName) => {
    setRunningAgentIndex(index);
    setApiError(null);
    const newResponses = { ...workgroupResponses };
    delete newResponses[agentName];
    setWorkgroupResponses(newResponses);
    const input = formData.io.input || "Please proceed with your task.";
    const result = await runAgent({
      input,
      workgroup: formData.workgroup,
      workgroupresponse: newResponses,
      targetAgentName: agentName
    });
    if (result.error) {
      console.error(result.error);
      setApiError(`Failed to run agent ${agentName}: ${result.error}`);
    } else {
      setWorkgroupResponses(result.data);
    }
    setRunningAgentIndex(null);
  };

  const handleRunWorkgroup = () => {
    if (!isPublishable) return; // Adicionado para segurança, mas o botão já estará desabilitado

    const responseformat = formData.step2.groups.reduce((acc, group) => {
      if (group.key && group.key.trim() !== "") acc[group.key.trim()] = group.description;
      return acc;
    }, {});

    const chaplinDataForModal = {
      name: formData.name || "Untitled Chaplin",
      instructions: formData.instructions || "No instructions provided.",
      avatarUrl: formData.avatarUrl,
      workgroup: formData.workgroup,
      responseformat: Object.keys(responseformat).length > 0 ? responseformat : { speech: "character's response to message" },
    };

    setTryModalChaplin(chaplinDataForModal);
    setIsTryModalOpen(true);
  };

  const handleTryModalSave = (results) => {
    setWorkgroupResponses(prev => ({ ...prev, ...results }));
  };

  const handleMobileNavClick = () => {
    if (window.innerWidth < 1024) setIsNavbarOpen(false);
  };

  const handleSpecialistPromptChange = (index, newPrompt) => {
    setFormData(prevData => {
      const newWorkgroup = [...prevData.workgroup];
      if (newWorkgroup[index]) {
        newWorkgroup[index] = { ...newWorkgroup[index], prompt: newPrompt };
      }
      return { ...prevData, workgroup: newWorkgroup };
    });
  };

  const handleSpecialistNameChange = (index, newName) => {
    setFormData(prevData => {
      const newWorkgroup = [...prevData.workgroup];
      if (newWorkgroup[index]) {
        const oldName = newWorkgroup[index].name;
        newWorkgroup[index] = { ...newWorkgroup[index], name: newName };

        if (oldName in workgroupResponses) {
          const newResponses = { ...workgroupResponses };
          newResponses[newName] = newResponses[oldName];
          delete newResponses[oldName];
          setWorkgroupResponses(newResponses);
        }
      }
      return { ...prevData, workgroup: newWorkgroup };
    });
  };

  function handleOpenModal(fieldIdentifier) {
    setEditingField(fieldIdentifier);
    setShowModal(true);
    setIsAvatarMenuOpen(false);
    setIsCategoryOpen(false);
  }

  function handleCloseModal() {
    setShowModal(false);
    setEditingField(null);
  }

  function handleSaveModal(newText) {
    if (!editingField) return;
    const { type, index } = editingField;
    setFormData((prevData) => {
      const newData = { ...prevData };
      if (type === "description") {
        newData.personaDescription = newText;
      } else if (type === "specialist") {
        const newWorkgroup = [...newData.workgroup];
        newWorkgroup[index] = { ...newWorkgroup[index], prompt: newText };
        newData.workgroup = newWorkgroup;
      } else if (type === "io_input") {
        newData.io = { ...newData.io, input: newText };
      } else if (type === "step2_key") {
        const groups = [...newData.step2.groups];
        groups[index] = { ...groups[index], key: newText.slice(0, STEP2_KEY_MAX) };
        newData.step2.groups = groups;
      } else if (type === "step2_description") {
        const groups = [...newData.step2.groups];
        groups[index] = { ...groups[index], description: newText.slice(0, STEP2_DESC_MAX) };
        newData.step2.groups = groups;
      }
      return newData;
    });
  }

  const getModalConfig = useCallback(() => {
    if (!editingField) return null;
    const { type, index } = editingField;
    const agentName = formData.workgroup[index]?.name || 'Specialist';

    switch (type) {
      case 'specialist':
        return {
          Icon: SquareCode,
          title: "Edit Prompt",
          subtitle: `Edit ${agentName}'s key content.`,
          initialText: formData.workgroup[index]?.prompt || "",
          actionButtonText: "Finish Editing",
          showActionButton: true,
          showAiHelper: true,
          maxLength: PROMPT_SPECIALIST_MAX,
        };
      case 'specialist_response':
        const responseAgentName = formData.workgroup[index]?.name;
        return {
          Icon: TextSearch,
          title: responseAgentName,
          subtitle: `Inspect the response of ${responseAgentName} below.`,
          initialText: workgroupResponses[responseAgentName] || "No response generated yet.",
          readOnly: true,
          showActionButton: false,
          showAiHelper: false,
        };
      case 'description':
        return {
          Icon: SquareCode,
          title: "Edit Prompt",
          subtitle: "Edit chaplin description content.",
          initialText: formData.personaDescription,
          maxLength: INSTR_MAX,
          actionButtonText: "Finish Editing",
          showAiHelper: true,
        };
      case 'step2_key':
        return {
          Icon: SquareCode,
          title: "Edit Prompt",
          subtitle: "Edit the content for this key.",
          initialText: formData.step2.groups[index]?.key || "",
          maxLength: STEP2_KEY_MAX,
          actionButtonText: "Finish Editing",
          showAiHelper: false,
        };
      case 'step2_description':
        return {
          Icon: SquareCode,
          title: "Edit Prompt",
          subtitle: "Edit the content for this description.",
          initialText: formData.step2.groups[index]?.description || "",
          maxLength: STEP2_DESC_MAX,
          actionButtonText: "Finish Editing",
          showAiHelper: false,
        };
      default:
        return { initialText: "" };
    }
  }, [editingField, formData.workgroup, formData.personaDescription, formData.step2.groups, workgroupResponses]);

  function addStep2Group() {
    setFormData((prev) => {
      const groups = [...prev.step2.groups];
      if (groups.length >= MAX_STEP2_GROUPS) return prev;
      groups.push({ key: "", description: "" });
      return { ...prev, step2: { ...prev.step2, groups } };
    });
  }

  function removeStep2Group(i) {
    setFormData((prev) => {
      if (prev.step2.groups.length === 1) {
        return { ...prev, step2: { ...prev.step2, groups: [{ key: "", description: "" }] } };
      }
      const groups = prev.step2.groups.filter((_, idx) => idx !== i);
      return { ...prev, step2: { ...prev.step2, groups } };
    });
  }

  function updateStep2Field(i, field, value) {
    setFormData((prev) => {
      const groups = [...prev.step2.groups];
      groups[i] = { ...groups[i], [field]: value };
      return { ...prev, step2: { ...prev.step2, groups } };
    });
  }

  function toggleCategory() {
    setIsCategoryOpen((s) => !s);
    setIsAvatarMenuOpen(false);
  }

  function selectCategory(value) {
    setFormData((prev) => ({ ...prev, category: value }));
    setIsCategoryOpen(false);
  }

  return (
    <SimpleBar style={{ maxHeight: '100vh' }} className="login-page-scrollbar">
      <div className="bg-[#18181B] min-h-screen font-inter text-[#D0D0D0]">
        <CreateModal
          isOpen={showModal}
          onClose={handleCloseModal}
          onSave={handleSaveModal}
          config={getModalConfig()}
        />
        {isTryModalOpen && (
          <TryModal
            chaplin={tryModalChaplin}
            onClose={() => setIsTryModalOpen(false)}
            onSaveResults={handleTryModalSave}
          />
        )}
        <PersonaNavbar isOpen={isNavbarOpen} setIsOpen={setIsNavbarOpen} viewMode={viewMode} setViewMode={setViewMode} handleMobileNavClick={handleMobileNavClick} />

        <button
          onClick={() => setIsNavbarOpen(true)}
          className={`fixed top-5 left-2 z-20 p-2 rounded-full cursor-pointer hover:bg-[#1F1F22] transition-opacity ${isNavbarOpen && window.innerWidth < 1024 ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
          aria-label="Open navigation menu"
        >
          <Menu color="#A2A2AB" size={23} />
        </button>

        <main className={`transition-all duration-300 ease-in-out ${isNavbarOpen ? "lg:ml-[260px]" : "lg:ml-0"}`}>
          <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 lg:py-7 py-5">

            <div className="flex flex-wrap items-center justify-between gap-y-4 mb-5">
              <h1 className="font-inter font-semibold text-xl text-[#FAFAFA] w-full lg:w-auto order-last lg:order-first">
                Create
              </h1>

              <div className="relative group ml-auto">
                <button
                  onClick={handlePublish}
                  disabled={!isPublishable || isPublishing}
                  className={`px-5 py-2 rounded-full font-medium transition-colors duration-300 ${isPublishable
                    ? 'bg-[#FAFAFA] text-black cursor-pointer hover:bg-[#E4E4E5]'
                    : 'bg-[#8D8D8F] text-[#18181B] cursor-not-allowed opacity-50'
                    } ${isPublishing && 'opacity-70 cursor-wait'}`}
                >
                  {isPublishing ? "Publishing..." : "Publish"}
                </button>
                {!isPublishable && (
                  <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-max max-w-xs bg-[#26272B] rounded-lg p-3 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 border border-[#303136] shadow-lg">
                    {tooltipMessage}
                    <svg
                      className="absolute text-[#26272B] h-2 w-full left-0 bottom-full"
                      x="0px"
                      y="0px"
                      viewBox="0 0 255 255"
                    >
                      <polygon className="fill-current" points="0,255 127.5,127.5 255,255" />
                    </svg>
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-col gap-4 max-w-xl">
              <div>
                <label className="text-sm text-[#FAFAFA]">Name</label>
                <div className="mt-2">
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value.slice(0, NAME_MAX) })}
                    placeholder="e.g. Charles Chaplin"
                    className="w-full text-sm bg-transparent border border-[#3A3A3A] text-white rounded-xl px-4 py-4 outline-none focus:ring-1 focus:ring-[#FAFAFA]"
                    maxLength={NAME_MAX}
                  />
                  <div className="w-full flex justify-end mt-1">
                    <div className="text-xs text-[#8C8C8C] select-none">{formData.name.length}/{NAME_MAX}</div>
                  </div>
                </div>
              </div>

              <div>
                <label className="text-sm text-[#FAFAFA]">Category</label>
                <div className="mt-2 relative pb-3" ref={categoryRef}>
                  <button
                    onClick={toggleCategory}
                    className={`w-full flex items-center justify-between bg-transparent border border-[#3A3A3A] rounded-xl text-sm  px-4 py-4 text-left focus:ring-1 focus:ring-[#FAFAFA] cursor-pointer ${formData.category ? "text-white" : "text-[#A3A3A3]"}`}
                    aria-haspopup="listbox"
                    aria-expanded={isCategoryOpen}
                  >
                    <span className={`${formData.category ? "" : "text-[#A3A3A3]"}`}>{formData.category || "Select your Chaplin category"}</span>
                    <ChevronDown size={18} className={`${isCategoryOpen ? "rotate-180" : "rotate-0"} transition-transform`} />
                  </button>
                  {isCategoryOpen && (
                    <div ref={categoryMenuRef} className="absolute z-50 mt-2 w-full bg-[#202024] rounded-lg shadow-lg overflow-hidden">
                      <SimpleBar className="category-dropdown-scrollbar" style={{ maxHeight: '14.5rem' }}>
                        <ul className="p-1 pr-2.5" role="listbox">
                          {CATEGORY_OPTIONS.map((opt) => (
                            <li key={opt}>
                              <button className="w-full text-left px-3 py-3 rounded-lg hover:bg-[#2C2C30] text-white focus:bg-[#2B2B2B] transition cursor-pointer text-sm" onClick={() => selectCategory(opt)}>{opt}</button>
                            </li>
                          ))}
                        </ul>
                      </SimpleBar>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <label className="text-sm text-[#FAFAFA]">Instructions</label>
                <div className="mt-2">
                  <textarea
                    value={formData.instructions}
                    onChange={(e) => setFormData({ ...formData, instructions: e.target.value.slice(0, INSTR_MAX) })}
                    placeholder="How this Chaplin works?"
                    className="instructions-scrollbar w-full bg-transparent border border-[#3A3A3A] text-white text-sm rounded-xl px-4 py-4 outline-none resize-none focus:ring-1 focus:ring-[#FAFAFA]"
                    rows={4}
                    maxLength={INSTR_MAX}
                  />
                  <div className="w-full flex justify-end mt-1">
                    <div className="text-xs text-[#8C8C8C] select-none">{formData.instructions.length}/{INSTR_MAX}</div>
                  </div>
                </div>
              </div>

              <div>
                <label className="text-sm text-[#FAFAFA]">Visibility</label>
                <button className="flex items-center gap-1.5 border border-[#3A3A3A] p-2.5 px-3 rounded-lg mt-2 text-sm text-[#FAFAFA] w-fit bg-transparent cursor-pointer">
                  <Globe color="#FAFAFA" size={16} />
                  Public
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-14">
              <div>
                <div className="mb-3"><div className="text-4xl font-semibold text-[#2E2E31] select-none">Step 1</div></div>
                <div className="border border-[#3A3A3A] rounded-xl">
                  <div className="px-4 py-5"><div className="flex items-center justify-between"><div className="text-[#FAFAFA] font-medium text-sm">Input Data</div></div></div>
                  <div className="h-px w-full bg-[#3A3A3A]" />
                  <div className="p-4 mt-2">
                    <div className="flex flex-col gap-3 mb-4">
                      <label className="text-xs text-white">Chaplin Description</label>
                      <ExpandableInput
                        value={formData.personaDescription}
                        onChange={(e) => setFormData({ ...formData, personaDescription: e.target.value.slice(0, INSTR_MAX) })}
                        placeholder="Describe your Chaplin"
                        maxLength={INSTR_MAX}
                        onOpenModal={() => handleOpenModal({ type: "description" })}
                      />
                    </div>
                    <div className="flex flex-col gap-2">
                      <label className="text-xs text-white">Avatar</label>
                      <div className="relative w-37 h-42">
                        <img src={formData.avatarUrl} alt="persona" className="w-full h-full object-cover rounded-3xl select-none" />
                        {isGeneratingAvatar && (<div className="absolute inset-0 bg-black/60 flex items-center justify-center rounded-3xl"><Loader2 className="w-8 h-8 text-white animate-spin" /></div>)}
                        <div className="absolute bottom-0 right-0">
                          <button ref={avatarButtonRef} onClick={() => setIsAvatarMenuOpen(prev => !prev)} className="bg-[#26272B] p-3 shadow-md rounded-full transition-colors cursor-pointer" aria-label="Avatar options" aria-expanded={isAvatarMenuOpen}><PenLine size={16} color="#F3F3F3" /></button>
                        </div>
                        {isAvatarMenuOpen && (
                          <div ref={avatarMenuRef} className="absolute bottom-4 left-37.5 z-50 w-56 bg-[#202024] rounded-lg p-1 shadow-lg">
                            <button onClick={handleGenerateImage} disabled={isGeneratingAvatar} className="flex justify-between items-center gap-2 w-full text-left px-3 py-2.5 rounded-lg text-sm hover:bg-[#2C2C30] transition cursor-pointer">
                              {isGeneratingAvatar ? "Generating..." : "Generate image"}
                              <WandSparkles size={14} color="#D9D3D3" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-3 flex items-center justify-between"><div className="text-4xl font-semibold text-[#2E2E31] select-none">Step 2</div></div>
                <div className="border border-[#3A3A3A] rounded-xl">
                  <div className="px-4 py-3">
                    <div className="flex items-center justify-between">
                      <div className="text-[#FAFAFA] font-medium text-sm flex items-center gap-3"><span>Output Format</span></div>
                      <div><button onClick={addStep2Group} className="p-2 rounded-full hover:bg-[#2C2C30] transition duration-200 active:scale-95 cursor-pointer" aria-label="Add key/description" title="Add key/description" disabled={formData.step2.groups.length >= MAX_STEP2_GROUPS}><Plus size={20} /></button></div>
                    </div>
                  </div>
                  <div className="h-px w-full bg-[#3A3A3A]" />
                  <div className="p-4">
                    <div className="flex flex-col gap-4">
                      {formData.step2.groups.map((grp, idx) => (
                        <div key={idx} className="border border-[#3A3A3A] rounded-xl p-3">
                          <div className="flex justify-between items-center mb-3">
                            <span className="text-[#797A86] text-sm font-regular">Output {idx + 1}</span>
                            <button onClick={() => removeStep2Group(idx)} className="p-2 rounded-full hover:bg-[#2C2C30] transition duration-200 active:scale-95 cursor-pointer" aria-label={`Remove group ${idx + 1}`}><Trash2 size={16} color="#A3A3A3" /></button>
                          </div>
                          <div className="flex flex-col items-start gap-4">
                            <div className="flex flex-col w-full gap-2">
                              <label className="text-xs text-white">key</label>
                              <ExpandableInput
                                value={grp.key}
                                onChange={(e) => updateStep2Field(idx, "key", e.target.value.slice(0, STEP2_KEY_MAX))}
                                placeholder="Name"
                                maxLength={STEP2_KEY_MAX}
                                onOpenModal={() => handleOpenModal({ type: "step2_key", index: idx })}
                              />
                            </div>
                            <div className="flex flex-col w-full gap-2">
                              <label className="text-xs text-white">description</label>
                              <ExpandableInput
                                value={grp.description}
                                onChange={(e) => updateStep2Field(idx, "description", e.target.value.slice(0, STEP2_DESC_MAX))}
                                placeholder="Describe the key"
                                maxLength={STEP2_DESC_MAX}
                                onOpenModal={() => handleOpenModal({ type: "step2_description", index: idx })}
                              />
                            </div>
                          </div>
                        </div>
                      ))}
                      {formData.step2.groups.length >= MAX_STEP2_GROUPS && (<div className="text-xs text-center text-[#8C8C8C] mt-2">Max {MAX_STEP2_GROUPS} keys allowed.</div>)}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-3"><div className="text-4xl font-semibold text-[#2E2E31] select-none">Step 3</div></div>
                <div className="border border-[#3A3A3A] rounded-xl">
                  <div className="px-4 py-[13px]">
                    <div className="flex items-center justify-between">
                      <div className="text-[#FAFAFA] text-sm font-medium">Workgroup</div>
                      <div className="flex gap-3">
                        <button onClick={handleGenerateWorkgroup} disabled={isGenerating} className="flex items-center gap-2 px-3 py-1.5 bg-transparent border border-[#3A3A3A] text-sm text-[#D9D3D3] font-semibold rounded-full cursor-pointer hover:bg-[#1F1F22] transition duration-200 active:scale-95 select-none disabled:cursor-not-allowed" title="AI Generate">
                          {isGenerating ? (
                            <Loader2 color="#EFEFEF" size={14} className="animate-spin" />
                          ) : (
                            <WandSparkles size={14} color="#D9D3D3" />
                          )}
                          {isGenerating ? "Generating..." : "AI Generate"}
                        </button>
                        {/* INÍCIO DA MODIFICAÇÃO */}
                        <div className="relative group">
                          <button
                            onClick={handleRunWorkgroup}
                            disabled={!isPublishable || isGenerating}
                            className={`flex items-center gap-2 px-3 py-1.5 bg-[#202024] text-[#D9D9D9] text-sm font-semibold rounded-full transition duration-200 active:scale-95 select-none ${isPublishable && !isGenerating
                                ? 'cursor-pointer hover:bg-[#3B3B42]'
                                : 'cursor-not-allowed opacity-50'
                              }`}
                            title="Run Workgroup"
                          >
                            <Play size={8} fill="#D9D9D9" />
                            Run
                          </button>
                          {!isPublishable && (
                            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-max max-w-xs bg-[#26272B] rounded-lg p-3 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 border border-[#303136] shadow-lg">
                              {tooltipMessage}
                              <svg
                                className="absolute text-[#26272B] h-2 w-full left-0 bottom-full"
                                x="0px"
                                y="0px"
                                viewBox="0 0 255 255"
                              >
                                <polygon className="fill-current" points="0,255 127.5,127.5 255,255" />
                              </svg>
                            </div>
                          )}
                        </div>
                        {/* FIM DA MODIFICAÇÃO */}
                      </div>
                    </div>
                  </div>
                  <div className="h-px w-full bg-[#3A3A3A]" />
                  <div className="p-4">
                    <WorkGroup
                      workgroupData={formData.workgroup}
                      workgroupResponses={workgroupResponses}
                      runningAgentIndex={runningAgentIndex}
                      onRunAgent={handleRunAgent}
                      onOpenSpecialistModal={(index) => handleOpenModal({ type: "specialist", index })}
                      onOpenResponseModal={(index) => handleOpenModal({ type: "specialist_response", index })}
                      isGenerating={isGenerating}
                      onPromptChange={handleSpecialistPromptChange}
                      onNameChange={handleSpecialistNameChange}
                    />
                  </div>
                </div>
              </div>
            </div>
            {apiError && <div className="text-red-500 text-sm mt-4">{apiError}</div>}
            <div className="h-10" />
          </div>
        </main>
      </div>
    </SimpleBar>
  );
}
export default Create;