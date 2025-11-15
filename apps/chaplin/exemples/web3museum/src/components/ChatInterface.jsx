import React from 'react';
import { Search, LoaderCircle } from 'lucide-react';
import { SendSolid } from 'iconoir-react';
import HomeImage from '../assets/home.png';
import HoloCard from './HoloCard';


const ChatInput = ({ userInput, setUserInput, handleSendMessage, isProcessing }) => (
    <div className="w-full max-w-2xl mx-auto">
        <div className="relative shadow-[0_0_900px_50px_rgba(108,56,172,0.4)] rounded-full">
            {isProcessing ? (

                <div
                    className="font-mono text-sm w-full bg-[#0C0B0F] text-[#703172] rounded-full py-4 px-6 border border-[#2b2031] flex items-center justify-center gap-3 transition-all"
                >
                    <LoaderCircle size={16} className="animate-spin" />
                    <span>Generating...</span>
                </div>
            ) : (

                <>
                    <Search size={14} color='#3E394B' className="absolute left-6 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                        type="text"
                        value={userInput}
                        onChange={(e) => setUserInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                        placeholder="Search"
                        disabled={isProcessing}
                        className="font-mono text-sm w-full bg-[#0C0B0F] text-white placeholder:text-[#3E394B] rounded-full py-4 pl-14 pr-16 border border-[#2b2031] focus:outline-none focus:ring-1 focus:ring-[#9b48ac] transition-all"
                    />
                    <button
                        onClick={handleSendMessage}
                        disabled={!userInput.trim()} // A prop 'isProcessing' não é mais necessária aqui
                        className="absolute right-1.5 top-1/2 -translate-y-1/2 bg-white w-11 h-11 flex items-center justify-center rounded-full hover:bg-gray-200 transition-colors cursor-pointer"
                    >
                        <SendSolid height={15} width={15} color='#242424' />
                    </button>
                </>
            )}
        </div>
    </div>
);



const MuseumDisplay = ({ imageUrl, result, originalInput, userInput, setUserInput, handleSendMessage, isProcessing }) => (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 text-white">
        <h1 class="flex items-center mb-12">
            <span class="font-mono font-regular bg-[#301A32] text-[#B032BC] text-xs mr-2 px-2 py-1 rounded-lg border border-[#4A2B4D]">Web3</span>
            <span class="text-[#faf6ff] text-xl">Digital Museum</span>
        </h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center max-w-5xl w-full">
            <div className="w-full h-[600px] aspect-[1/1.4] cursor-pointer">
                {imageUrl ? (
                    <HoloCard imageUrl={imageUrl} title={originalInput} />
                ) : (
                    <div className="flex items-center justify-center h-full bg-[#5d2e63] rounded-2xl animate-pulse">
                        <p className="text-[#7e3288]">Loading Card...</p>
                    </div>
                )}
            </div>
            <div className="flex justify-end flex-col gap-4">
                <h2 className="text-2xl font-semibold text-[#f4effd]">{originalInput}</h2>
                <p className="text-[#EFE7FE] font-medium leading-relaxed">
                    {result.museum_label}
                </p>
            </div>
        </div>
        <div className="mt-16 w-full">
            <ChatInput
                userInput={userInput}
                setUserInput={setUserInput}
                handleSendMessage={handleSendMessage}
                isProcessing={isProcessing}
            />
        </div>
    </div>
);

// Tela Inicial
const InitialScreen = ({ userInput, setUserInput, handleSendMessage, isProcessing }) => (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
        <div className="bg-[#060606] border border-[#312637] rounded-3xl overflow-hidden max-w-lg w-full">
            <img src={HomeImage} alt="Web3 Digital Museum" className="w-full h-auto object-cover" />
            <hr className="border-[#312637]" />
            <div className="flex flex-col p-8 gap-1">
                <h1 class="flex items-center mb-2">
                    <span class="font-mono font-regular bg-[#301A32] text-[#B032BC] text-xs mr-2 px-2 py-1 rounded-lg border border-[#4A2B4D]">Web3</span>
                    <span className="text-[#faf6ff] text-xl">Digital Museum</span>
                </h1>
                <p className="font-mono font-semibold text-[#672c69] mb-8 text-sm">Search for an object, person or historical event</p>

                <ChatInput
                    userInput={userInput}
                    setUserInput={setUserInput}
                    handleSendMessage={handleSendMessage}
                    isProcessing={isProcessing}
                />
            </div>
        </div>
    </div>
);


// Componente principal
export default function ChatInterface({
    isProcessing,
    finalResult,
    generatedImageUrl,
    userInput,
    setUserInput,
    handleSendMessage,
    originalInput
}) {
    if (finalResult) {
        return <MuseumDisplay
            imageUrl={generatedImageUrl}
            result={finalResult}
            originalInput={originalInput}
            userInput={userInput}
            setUserInput={setUserInput}
            handleSendMessage={handleSendMessage}
            isProcessing={isProcessing}
        />;
    }

    return <InitialScreen
        userInput={userInput}
        setUserInput={setUserInput}
        handleSendMessage={handleSendMessage}
        isProcessing={isProcessing}
    />;
}