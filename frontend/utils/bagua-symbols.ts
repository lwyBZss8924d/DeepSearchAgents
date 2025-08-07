/**
 * Bagua (八卦) Trigram Symbol Utilities
 * 
 * Maps step numbers to traditional Chinese Bagua trigrams for WebTUI badges
 */

// The 8 Bagua trigrams in order
const BAGUA_TRIGRAMS = [
  '☰', // TRIGRAM FOR HEAVEN (乾 qián)
  '☱', // TRIGRAM FOR LAKE (兑 duì)
  '☲', // TRIGRAM FOR FIRE (离 lí)
  '☳', // TRIGRAM FOR THUNDER (震 zhèn)
  '☴', // TRIGRAM FOR WIND (巽 xùn)
  '☵', // TRIGRAM FOR WATER (坎 kǎn)
  '☶', // TRIGRAM FOR MOUNTAIN (艮 gèn)
  '☷', // TRIGRAM FOR EARTH (坤 kūn)
] as const;

// Agent event type symbols
export const AGENT_SYMBOLS = {
  PLANNING: '☯',        // Yin Yang symbol for planning steps
  FINAL_ANSWER: '🀅',   // Mahjong Green Dragon for final answer
  CODE_ACTION: '~Py',   // ASCII symbol for code actions
  COMMAND: '⌘',         // Command symbol for tool calls
} as const;

/**
 * Get the Bagua trigram for a given step number
 * Maps steps 1-99 to one of 8 trigrams using modulo
 * 
 * @param stepNumber - The step number (1-99)
 * @returns The corresponding Bagua trigram symbol
 */
export function getBaguaTrigram(stepNumber: number): string {
  // Handle edge cases
  if (stepNumber < 1) return BAGUA_TRIGRAMS[0];
  if (stepNumber > 99) stepNumber = stepNumber % 100 || 1;
  
  // Map to 0-7 index (step 1 = index 0, step 8 = index 7, step 9 = index 0, etc.)
  const index = (stepNumber - 1) % 8;
  return BAGUA_TRIGRAMS[index];
}

/**
 * Format a planning badge with Yin Yang symbol
 * 
 * @param isInitial - Whether this is the initial plan
 * @returns Formatted planning badge string
 */
export function formatPlanningBadge(isInitial: boolean): string {
  const planType = isInitial ? 'Initial Plan' : 'Updated Plan';
  return `${AGENT_SYMBOLS.PLANNING} (${planType})`;
}

/**
 * Format an action badge with Bagua trigram
 * 
 * @param stepNumber - The step number
 * @param toolName - The tool name to display
 * @param isCodeAction - Whether this is a code action
 * @returns Formatted action badge string
 */
export function formatActionBadge(
  stepNumber: number, 
  toolName: string, 
  isCodeAction: boolean = false
): string {
  const trigram = getBaguaTrigram(stepNumber);
  
  if (isCodeAction) {
    return `${trigram} ${AGENT_SYMBOLS.CODE_ACTION} ${AGENT_SYMBOLS.COMMAND}(${toolName})`;
  } else {
    return `${trigram} ${AGENT_SYMBOLS.COMMAND}(${toolName})`;
  }
}

/**
 * Format a final answer badge with Mahjong Green Dragon
 * 
 * @returns Formatted final answer badge string
 */
export function formatFinalAnswerBadge(): string {
  return `${AGENT_SYMBOLS.FINAL_ANSWER} (Final Answer)`;
}