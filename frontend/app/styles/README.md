# Tailwind CSS Architecture

## Overview
This directory contains the refactored Tailwind CSS architecture with improved structure, scalability, and semantic clarity.

## File Structure

### `design-tokens.css`
Central source of truth for all design tokens including:
- **Semantic Color Tokens**: Named color values with clear purpose
- **Gray Scale**: Comprehensive gray palette from 50-900
- **Brand Colors**: Primary and secondary brand colors
- **Semantic Colors**: danger, warning, info, success variants
- **Chart Colors**: Dedicated palette for data visualization
- **Spacing & Typography**: Consistent spacing and font configurations

### `animations.css`
Reusable animation utilities:
- **Keyframes**: fadeIn, fadeOut, slideIn, scaleIn, shimmer, etc.
- **Utility Classes**: Ready-to-use animation classes with modifiers
- **Animation Modifiers**: Delay and duration utilities

### `utilities.css`
Custom utility classes:
- **Text Utilities**: Balance, wrapping controls
- **Gradient Presets**: Reusable gradient patterns
- **Scrollbar Styling**: Custom scrollbar appearance
- **Glass Morphism**: Modern blur effects
- **Loading States**: Skeleton loaders

### `globals.css`
Main entry point that:
- Imports all modular CSS files
- Configures Tailwind plugins
- Sets up base styles
- Maps CSS variables to Tailwind theme

## Key Improvements

1. **Semantic Naming**
   - Colors now have meaningful names (e.g., `--color-danger`, `--color-brand-primary`)
   - Clear distinction between UI colors and semantic colors

2. **Modular Organization**
   - Separated concerns into dedicated files
   - Easier to maintain and scale
   - Clear import hierarchy

3. **Standardized Dark Mode**
   - Uses Tailwind's built-in `.dark` class strategy
   - All theme values properly mapped for both light and dark modes

4. **Removed Redundancy**
   - Eliminated duplicate color declarations
   - Consolidated theme mapping in one place
   - Removed unnecessary `@custom-variant` in favor of standard approach

5. **Animation System**
   - Animations moved to dedicated file
   - Reusable utility classes with consistent naming
   - Added animation modifiers for flexibility

## Usage Examples

### Using Semantic Colors
```css
/* Instead of: */
.element {
  color: oklch(0.577 0.245 27.325);
}

/* Use: */
.element {
  @apply text-destructive;
}
```

### Using Animations
```html
<!-- Fade in animation -->
<div class="animate-fadeIn">Content</div>

<!-- Delayed animation -->
<div class="animate-slideInLeft animation-delay-200">Content</div>

<!-- Custom duration -->
<div class="animate-scaleIn animation-duration-500">Content</div>
```

### Using Gradients
```html
<!-- Brand gradient -->
<div class="bg-gradient-brand">Content</div>

<!-- Custom gradient utility -->
<div class="bg-gradient-skyblue-lavender">Content</div>
```

## Migration Notes

The `tailwindcss-animate` plugin is still included but its usage should be reviewed. Consider whether the custom animation utilities provide sufficient coverage for your needs.