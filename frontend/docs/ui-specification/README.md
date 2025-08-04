# DSCS UI Specification Documentation

This directory contains the comprehensive UI/UX specification for DeepSearchAgents' Web-TUI interface.

## 📚 Documentation Structure

### Core Specifications

1. **[DSCS-UI-Specification.md](./DSCS-UI-Specification.md)**
   - Main comprehensive design specification
   - Visual design system and color palette
   - Component architecture overview
   - Animation and interaction patterns
   - Implementation guidelines

2. **[DSCS-WebTUI-Integration.md](./DSCS-WebTUI-Integration.md)**
   - WebTUI CSS library integration guide
   - CSS layer architecture
   - Style override patterns
   - Troubleshooting common issues

3. **[DSCS-Component-Library.md](./DSCS-Component-Library.md)**
   - Complete component API reference
   - Props documentation and TypeScript interfaces
   - Usage examples and best practices
   - Hooks and context providers

### Archive

The `archive/` directory contains previous versions of the design documentation for historical reference:
- Original Design Language specification
- Initial Design System specification
- Early UI/UX requirements

## 🚀 Quick Start

For developers implementing the UI:

1. Read the [main specification](./DSCS-UI-Specification.md) for design philosophy and visual system
2. Reference the [component library](./DSCS-Component-Library.md) for implementation details
3. Check the [WebTUI integration guide](./DSCS-WebTUI-Integration.md) for styling patterns

## 🎨 Design Philosophy

**"Code is Action!"** - Our Web-TUI interface makes AI agent operations transparent by:
- Showing real code execution
- Providing live status updates
- Using authentic terminal aesthetics
- Building trust through visibility

## 📦 Key Components

- `DSAgentStateBadge` - Agent status indicators
- `DSAgentMessageCard` - Message containers
- `DSAgentToolBadge` - Tool execution badges
- `DSAgentTimer` - Real-time execution timer
- `DSAgentRandomMatrix` - ASCII animation with cyberpunk effects

## 🔗 Related Resources

- [Frontend README](../../README.md)
- [Component Source](../../components/ds/)
- [Style Sheets](../../app/styles/)
- [WebTUI Documentation](https://webtui.dev)