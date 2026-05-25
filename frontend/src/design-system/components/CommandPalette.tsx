import React, { useState, useEffect, useRef } from "react";
import { TOKENS } from "../tokens";
import { Search } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import Fuse from "fuse.js";

interface CommandItem {
  id: string;
  category: "QUERY" | "CONNECTION" | "COMMAND";
  title: string;
  subtitle?: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  items: CommandItem[];
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  items
}) => {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Fuzzy search index using fuse.js
  const fuse = new Fuse(items, {
    keys: ["title", "subtitle", "category"],
    threshold: 0.4
  });

  const filteredItems = query ? fuse.search(query).map(r => r.item) : items.slice(0, 10);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % Math.max(1, filteredItems.length));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filteredItems[selectedIndex]) {
          filteredItems[selectedIndex].action();
          onClose();
        }
      } else if (e.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, filteredItems, selectedIndex, onClose]);

  const paletteStyles: React.CSSProperties = {
    fontFamily: TOKENS.fonts.ui,
    backgroundColor: TOKENS.colors.vault,
    border: `1px solid ${TOKENS.colors.border}`,
    borderRadius: TOKENS.radii.md,
    boxShadow: "0 10px 40px rgba(0,0,0,0.6)",
    width: "600px",
    maxHeight: "450px",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    zIndex: 1000
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 flex items-start justify-center pt-24 z-[999]">
          <motion.div
            className="fixed inset-0 bg-black/60 backdrop-blur-md"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            style={paletteStyles}
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ duration: 0.15 }}
          >
            <div
              className="flex items-center px-4 py-3 border-b"
              style={{ borderColor: TOKENS.colors.border }}
            >
              <Search className="text-text-secondary mr-3" size={18} />
              <input
                ref={inputRef}
                type="text"
                placeholder="Search queries, connections, commands..."
                value={query}
                onChange={e => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                className="w-full bg-transparent border-none outline-none text-text-primary text-sm placeholder-text-muted"
              />
            </div>
            
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {filteredItems.length > 0 ? (
                filteredItems.map((item, idx) => {
                  const isSelected = idx === selectedIndex;
                  return (
                    <div
                      key={item.id}
                      onClick={() => {
                        item.action();
                        onClose();
                      }}
                      className="flex items-center justify-between px-3 py-2 cursor-pointer select-none"
                      style={{
                        backgroundColor: isSelected ? `${TOKENS.colors.ember}1F` : "transparent",
                        borderLeft: isSelected ? `2px solid ${TOKENS.colors.ember}` : "2px solid transparent"
                      }}
                    >
                      <div>
                        <div className="text-xs font-semibold text-text-primary">
                          {item.title}
                        </div>
                        {item.subtitle && (
                          <div className="text-[10px] text-text-secondary mt-0.5 truncate max-w-[450px]">
                            {item.subtitle}
                          </div>
                        )}
                      </div>
                      <span
                        className="text-[9px] font-bold tracking-widest uppercase border px-2 py-0.5 rounded"
                        style={{
                          borderColor: TOKENS.colors.border,
                          color: TOKENS.colors.text.muted
                        }}
                      >
                        {item.category}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-6 text-xs text-text-muted">
                  No matching items found
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
