import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader2, Database, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function SherlockChatInterface() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your Sherlock Domestic Account Analysis Assistant. I can help you analyze account balances, overdraft positions, tenure data, and more. What would you like to know?',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('');
  const [toolStatus, setToolStatus] = useState(null);
  const messagesEndRef = useRef(null);
  const wsRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentStreamingMessage]);

  const connectWebSocket = () => {
    // Replace with your actual WebSocket URL
    const ws = new WebSocket('ws://localhost:8080/ws/chat');
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'text') {
        setCurrentStreamingMessage(prev => prev + data.content);
      } else if (data.type === 'tool_call') {
        setToolStatus({
          tool: data.tool,
          status: data.status,
          input: data.input
        });
      } else if (data.type === 'done') {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: currentStreamingMessage,
            timestamp: new Date()
          }
        ]);
        setCurrentStreamingMessage('');
        setIsStreaming(false);
        setToolStatus(null);
      } else if (data.type === 'error') {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `Error: ${data.message}`,
            timestamp: new Date(),
            isError: true
          }
        ]);
        setIsStreaming(false);
        setToolStatus(null);
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsStreaming(false);
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };
    
    wsRef.current = ws;
  };

  const handleSend = () => {
    if (!inputValue.trim() || isStreaming) return;
    
    const userMessage = {
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsStreaming(true);
    setCurrentStreamingMessage('');
    
    // Connect WebSocket if not connected
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      // Wait for connection
      setTimeout(() => {
        wsRef.current?.send(JSON.stringify({
          message: inputValue,
          history: messages.map(m => ({
            role: m.role,
            content: m.content
          }))
        }));
      }, 500);
    } else {
      wsRef.current.send(JSON.stringify({
        message: inputValue,
        history: messages.map(m => ({
          role: m.role,
          content: m.content
        }))
      }));
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestionQueries = [
    "Show me accounts with overdraft > $1M",
    "What's the total balance by country?",
    "Which accounts have overdraft tenure > 90 days?",
    "Show me the overdraft aging breakdown",
    "Top 10 accounts by balance"
  ];

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-semibold text-gray-900">
          Sherlock Account Analysis
        </h1>
        <p className="text-sm text-gray-600 mt-1">
          Domestic Account Data Intelligence Assistant
        </p>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-3xl rounded-2xl px-6 py-4 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : message.isError
                    ? 'bg-red-50 text-red-900 border border-red-200'
                    : 'bg-white text-gray-900 shadow-sm border border-gray-200'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                <div
                  className={`text-xs mt-2 ${
                    message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                  }`}
                >
                  {message.timestamp.toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}

          {/* Streaming Message */}
          {isStreaming && (
            <div className="flex justify-start">
              <div className="max-w-3xl rounded-2xl px-6 py-4 bg-white text-gray-900 shadow-sm border border-gray-200">
                {toolStatus && (
                  <div className="flex items-center gap-2 mb-3 pb-3 border-b border-gray-200">
                    {toolStatus.status === 'started' && (
                      <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                    )}
                    {toolStatus.status === 'executing' && (
                      <Database className="w-4 h-4 text-blue-600 animate-pulse" />
                    )}
                    {toolStatus.status === 'completed' && (
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                    )}
                    <span className="text-sm text-gray-600">
                      {toolStatus.status === 'started' && 'Preparing to analyze data...'}
                      {toolStatus.status === 'executing' && `Analyzing: ${toolStatus.input?.query || 'data'}...`}
                      {toolStatus.status === 'completed' && 'Analysis complete'}
                    </span>
                  </div>
                )}
                <div className="whitespace-pre-wrap">
                  {currentStreamingMessage}
                  <span className="inline-block w-2 h-5 bg-gray-900 ml-1 animate-pulse" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Suggestion Chips (show when no messages) */}
      {messages.length === 1 && !isStreaming && (
        <div className="px-4 pb-4">
          <div className="max-w-4xl mx-auto">
            <p className="text-sm text-gray-600 mb-3">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {suggestionQueries.map((query, idx) => (
                <button
                  key={idx}
                  onClick={() => setInputValue(query)}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-full text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-400 transition-colors"
                >
                  {query}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about accounts, balances, overdrafts, tenure..."
                disabled={isStreaming}
                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none disabled:bg-gray-50 disabled:text-gray-500"
                rows={1}
                style={{
                  minHeight: '52px',
                  maxHeight: '200px',
                  height: 'auto'
                }}
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || isStreaming}
              className="p-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
            >
              {isStreaming ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  );
}