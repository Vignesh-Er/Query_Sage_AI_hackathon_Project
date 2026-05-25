import React from "react";
import { TOKENS } from "../../design-system/tokens";
import { Button } from "../../design-system/components/Button";
import { MessageSquare, CornerDownLeft } from "lucide-react";

interface NLInputProps {
  value: string;
  onChange: (val: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

export const NLInput: React.FC<NLInputProps> = ({
  value,
  onChange,
  onSubmit,
  isLoading
}) => {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim()) {
        onSubmit();
      }
    }
  };

  return (
    <div className="relative border border-border bg-pitch p-3" style={{ fontFamily: TOKENS.fonts.ui }}>
      <div className="flex items-start gap-2.5">
        <MessageSquare size={16} className="text-textSecondary mt-2.5 shrink-0" />
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe the query you want in plain English (e.g., 'Find the top 5 customers who rented movies in 2005, sorted by rental count')"
          disabled={isLoading}
          rows={3}
          className="w-full bg-transparent text-textPrimary text-xs focus:outline-none resize-none font-medium leading-relaxed placeholder:text-textMuted"
        />
      </div>

      <div className="flex items-center justify-between border-t border-border/40 pt-2 mt-2">
        <span className="text-[10px] text-textMuted flex items-center gap-1 font-semibold select-none">
          <CornerDownLeft size={10} />
          Press Enter to generate SQL
        </span>
        <Button
          variant="primary"
          onClick={onSubmit}
          disabled={!value.trim() || isLoading}
          isLoading={isLoading}
          className="font-bold border border-ember h-7 text-[10px] tracking-wider uppercase px-4"
        >
          {isLoading ? "Translating..." : "Translate to SQL"}
        </Button>
      </div>
    </div>
  );
};
