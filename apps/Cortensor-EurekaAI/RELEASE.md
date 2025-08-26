# Release Notes

## Latest Release - Mobile Optimization & Dark Mode Focus

**Release Date:** August 8, 2025

This major release transforms Eureka AI into a mobile-first, professional dark-mode application with advanced keyboard handling and user experience improvements.

### ✨ Major Features

#### **🌙 Dark Mode Only**
- **Forced Dark Theme**: Removed light mode entirely for consistent professional appearance
- **Theme Toggle Removal**: Simplified interface without theme switching complexity
- **Optimized CSS**: Streamlined styling with dark-mode specific optimizations

#### **📱 Advanced Mobile Optimization**
- **Stable Keyboard Handling**: Fixed positioning system prevents layout jumps when keyboard appears
- **iOS Safari Compatibility**: Proper dynamic viewport height (100dvh) handling
- **Android Keyboard Support**: Optimized for various Android input methods
- **Touch-First Interface**: 48px minimum touch targets for accessibility compliance

#### **🎨 UI/UX Improvements**
- **Chat History Truncation**: Limited chat titles to 22 characters to prevent sidebar overflow
- **Glass Morphism Effects**: Modern backdrop blur and translucent components
- **Responsive Typography**: Optimized font sizes and line heights for mobile reading
- **Performance Optimizations**: Reduced bundle size and improved loading times

### 🔧 Technical Improvements

- **Fixed Positioning System**: Chat input uses stable positioning without transform-based movements
- **Debounced Keyboard Detection**: Smooth keyboard state management without performance issues
- **Optimized Rendering**: Reduced unnecessary re-renders and improved memory usage
- **Enhanced Error Handling**: Better error messages and recovery mechanisms

### 🐛 Bug Fixes

- **Mobile Layout Jumps**: Eliminated content shifting when mobile keyboard appears/disappears
- **Sidebar Overflow**: Fixed long chat titles breaking sidebar layout
- **Touch Target Issues**: Improved button sizes and touch responsiveness
- **iOS Scroll Issues**: Fixed momentum scrolling and safe area handling

---

## Previous Release - DeepSeek R1 Integration

**Release Date:** August 5, 2025

Major update focusing on advanced AI model integration and reasoning capabilities.

### ✨ Major Features

#### **🏗️ Robust Response Aggregation**
- **Rewritten Backend Logic**: Complete overhaul of response processing system
- **Multi-Miner Support**: Intelligent aggregation from multiple Cortensor miners
- **Smart Response Selection**: Automatic selection of most complete and accurate responses

#### **💾 Local-First Architecture**
- **Static Session Management**: Single persistent session ID from environment variables
- **Client-Side Chat History**: Browser-based storage for privacy and speed
- **Context Isolation**: Prevents conversation mixing between different chat sessions

#### **🎛️ Enhanced User Controls**
- **Memory Mode Toggle**: Direct user control over AI conversational memory
- **Improved Error Messages**: More specific and actionable error feedback
- **Better Loading States**: Clear indication of application status

### 🐛 Critical Bug Fixes

- **"No Valid Responses" Error**: Fixed parsing issues with mixed data streams
- **UI Initialization Lock**: Eliminated startup hanging on "Initializing..." screen
- **Disappearing Chat Messages**: Resolved state management issues causing message loss
- **Inconsistent AI Memory**: Fixed conflicting dual-prompt system behavior

### 🔧 Technical Improvements

- **Frontend State Management**: Cleaner, more maintainable React state logic
- **Error Handling**: Comprehensive error tracking and user feedback
- **Performance**: Faster startup times and improved responsiveness
