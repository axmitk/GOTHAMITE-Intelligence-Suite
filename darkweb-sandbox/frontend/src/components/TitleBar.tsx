import React from 'react';
import { Minus, Square, X } from 'lucide-react';

interface TitleBarProps {
  onMinimize?: () => void;
  onMaximize?: () => void;
  onClose?: () => void;
}

export const TitleBar: React.FC<TitleBarProps> = ({ onMinimize, onMaximize, onClose }) => {
  return (
    <header
      id="window-titlebar"
      className="h-9 bg-[#060e0f] border-b border-[#153634] flex items-center justify-between px-3.5 z-30 select-none shrink-0"
    >
      {/* Left Mac OS controls & Title */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2">
          <button
            onClick={onClose}
            title="Close"
            className="w-3 h-3 rounded-full bg-[#ff5f56] inline-block hover:opacity-80 transition-opacity cursor-pointer shadow-sm"
          />
          <button
            onClick={onMinimize}
            title="Minimize"
            className="w-3 h-3 rounded-full bg-[#ffbd2e] inline-block hover:opacity-80 transition-opacity cursor-pointer shadow-sm"
          />
          <button
            onClick={onMaximize}
            title="Maximize"
            className="w-3 h-3 rounded-full bg-[#27c93f] inline-block hover:opacity-80 transition-opacity cursor-pointer shadow-sm"
          />
        </div>
        <div className="text-[12px] font-mono tracking-wide text-gray-300 ml-2 font-medium flex items-center space-x-1.5">
          <span className="text-[#2bf0a6] font-semibold tracking-wider">GOTHAMITE</span>
          <span className="text-gray-500">•</span>
          <span className="text-gray-400">Dark Web Sandbox Browser</span>
        </div>
      </div>

      {/* Right Window Controls */}
      <div className="flex items-center space-x-3 text-gray-500 text-xs">
        <button
          onClick={onMinimize}
          className="hover:text-gray-200 transition-colors p-1"
          title="Minimize Window"
        >
          <Minus className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={onMaximize}
          className="hover:text-gray-200 transition-colors p-1"
          title="Maximize Window"
        >
          <Square className="w-3 h-3" />
        </button>
        <button
          onClick={onClose}
          className="hover:text-red-400 transition-colors p-1"
          title="Close Window"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
