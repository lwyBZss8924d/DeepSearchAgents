import { motion } from "framer-motion";
import { ArrowUp } from "lucide-react";
import { DSButton, DSTextarea } from "@/components/ds";
import { useEffect, useState } from "react";

interface EditQuestionProps {
  className?: string;
  textareaClassName?: string;
  editingMessage: string;
  handleCancel?: () => void;
  handleEditMessage: (newContent: string) => void;
}

const EditQuestionV2 = ({
  className,
  textareaClassName,
  editingMessage,
  handleCancel,
  handleEditMessage,
}: EditQuestionProps) => {
  const [newContent, setNewContent] = useState(editingMessage);

  useEffect(() => {
    setNewContent(editingMessage);
  }, [editingMessage]);

  const handleSend = () => {
    if (newContent.trim()) {
      handleEditMessage(newContent);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className={className}
    >
      <div className="flex gap-2">
        <DSTextarea
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Edit your question..."
          className={textareaClassName}
          minRows={2}
          maxRows={8}
        />
        <div className="flex flex-col gap-2">
          <DSButton
            onClick={handleSend}
            disabled={!newContent.trim()}
            variant="primary"
            size="sm"
            icon={<ArrowUp size={16} />}
            aria-label="Send edited message"
          />
          {handleCancel && (
            <DSButton
              onClick={handleCancel}
              variant="secondary"
              size="sm"
              aria-label="Cancel editing"
            >
              Cancel
            </DSButton>
          )}
        </div>
      </div>
    </motion.div>
  );
};

export default EditQuestionV2;