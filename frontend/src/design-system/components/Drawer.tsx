import React from "react";
import { TOKENS } from "../tokens";
import { X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  children
}) => {
  const drawerStyles: React.CSSProperties = {
    fontFamily: TOKENS.fonts.ui,
    backgroundColor: TOKENS.colors.vault,
    borderRight: `1px solid ${TOKENS.colors.border}`,
    height: "100%",
    width: "400px",
    position: "fixed",
    left: 0,
    top: 0,
    zIndex: 900,
    display: "flex",
    flexDirection: "column",
    boxShadow: "10px 0 30px rgba(0,0,0,0.5)"
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop blur overlay */}
          <motion.div
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[890]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            style={drawerStyles}
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
          >
            <div
              className="flex items-center justify-between p-4 border-b"
              style={{ borderColor: TOKENS.colors.border }}
            >
              <h3 className="text-sm font-semibold tracking-wider uppercase text-primary">
                {title}
              </h3>
              <button
                onClick={onClose}
                className="text-text-secondary hover:text-ember active:scale-95 transition-colors"
              >
                <X size={18} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">{children}</div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
