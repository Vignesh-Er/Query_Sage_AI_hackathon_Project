import React from "react";
import Editor, { loader } from "@monaco-editor/react";
import { TOKENS } from "../../design-system/tokens";
import { MONACO_THEME } from "../../design-system/monaco-theme";

loader.init().then((monaco) => {
  monaco.editor.defineTheme("querysage-theme", MONACO_THEME as any);
});

interface MonacoEditorComponentProps {
  value: string;
  onChange: (val: string) => void;
  onMount: (editor: any, monaco: any) => void;
}

export const MonacoEditorComponent: React.FC<MonacoEditorComponentProps> = ({
  value,
  onChange,
  onMount
}) => {
  return (
    <Editor
      value={value}
      onChange={(val) => onChange(val || "")}
      onMount={onMount}
      language="sql"
      theme="querysage-theme"
      options={{
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: "on",
        lineNumbers: "on",
        fontSize: 12,
        fontFamily: TOKENS.fonts.code,
        tabSize: 2,
        automaticLayout: true
      }}
    />
  );
};

export default MonacoEditorComponent;
