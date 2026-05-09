"""
Tests for AIChatWidget component.
Covers: messages render, loading state, add-to-cart callback, and API mocking.
"""

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AIChatWidget } from "@/components/AIChatWidget";

// Mock fetch globally
global.fetch = vi.fn();

describe("AIChatWidget", () => {
  const mockOnAddToCart = vi.fn();
  
  beforeEach(() => {
    // Mock localStorage
    Storage.prototype.getItem = vi.fn(() => "mock-token");
    
    // Mock successful API response
    (fetch as any).mockResolvedValue({
      ok: true,
      json: async () => ({
        response_text: "Here are some dishes you might like!",
        suggested_dishes: [
          {
            item_id: 1,
            name: "Spicy Chicken Tikka",
            reasoning: "Perfect for spice lovers",
            price: 18.99,
          },
          {
            item_id: 2,
            name: "Vegetable Curry",
            reasoning: "Healthy and flavorful",
            price: 14.99,
          },
        ],
        follow_up_question: "Would you like to see more options?",
        session_id: "test-session-123",
        agent: "deepseek-v4-flash",
      }),
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders floating launch button when closed", () => {
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    expect(screen.getByText("Let AI recommend me something")).toBeInTheDocument();
  });

  it("opens chat when launch button is clicked", async () => {
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    const launchButton = screen.getByText("Let AI recommend me something");
    fireEvent.click(launchButton);
    
    // Should show chat header
    await waitFor(() => {
      expect(screen.getByText("AI Food Assistant")).toBeInTheDocument();
    });
  });

  it("shows loading state while waiting for API response", async () => {
    // Delay the fetch response
    (fetch as any).mockImplementation(() => 
      new Promise((resolve) => setTimeout(resolve, 100))
    );
    
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Open chat
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    // Wait for loading indicator to appear
    await waitFor(() => {
      expect(screen.getByText(/AI is thinking/i)).toBeInTheDocument();
    });
  });

  it("renders user message after sending", async () => {
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Open chat
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Tell me what you're craving/i)).toBeInTheDocument();
    });
    
    // Type and send message
    const input = screen.getByPlaceholderText(/Tell me what you're craving/i);
    fireEvent.change(input, { target: { value: "I want something spicy" } });
    fireEvent.keyDown(input, { key: "Enter" });
    
    // Should show user message
    await waitFor(() => {
      expect(screen.getByText("I want something spicy")).toBeInTheDocument();
    });
  });

  it("renders AI response with suggested dishes", async () => {
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Open chat
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    await waitFor(() => {
      expect(screen.getByText("Here are some dishes you might like!")).toBeInTheDocument();
    });
    
    // Should show suggested dishes
    expect(screen.getByText("Spicy Chicken Tikka")).toBeInTheDocument();
    expect(screen.getByText("Vegetable Curry")).toBeInTheDocument();
  });

  it("triggers onAddToCart when 'Add to Cart' button is clicked", async () => {
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Open chat and wait for response
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    await waitFor(() => {
      expect(screen.getByText("Spicy Chicken Tikka")).toBeInTheDocument();
    });
    
    // Click Add to Cart on first dish
    const addToCartButtons = screen.getAllByText("Add to Cart");
    fireEvent.click(addToCartButtons[0]);
    
    // Should trigger callback with correct payload
    expect(mockOnAddToCart).toHaveBeenCalledWith({
      id: 1,
      name: "Spicy Chicken Tikka",
      price: 18.99,
    });
  });

  it("sends API request with correct payload", async () => {
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Open chat
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Tell me what you're craving/i)).toBeInTheDocument();
    });
    
    // Type and send message
    const input = screen.getByPlaceholderText(/Tell me what you're craving/i);
    fireEvent.change(input, { target: { value: "I want vegan food" } });
    fireEvent.keyDown(input, { key: "Enter" });
    
    // Wait for API call
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/recommendations/chat"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
            "Authorization": "Bearer mock-token",
          }),
          body: expect.stringContaining("I want vegan food"),
        })
      );
    });
  });

  it("includes session_id in subsequent requests", async () => {
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Open chat and get initial response
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    await waitFor(() => {
      expect(screen.getByText("Here are some dishes you might like!")).toBeInTheDocument();
    });
    
    // Send follow-up message
    const input = screen.getByPlaceholderText(/Tell me what you're craving/i);
    fireEvent.change(input, { target: { value: "What about drinks?" } });
    fireEvent.keyDown(input, { key: "Enter" });
    
    // Wait for second API call with session_id
    await waitFor(() => {
      const calls = (fetch as any).mock.calls;
      const lastCall = calls[calls.length - 1];
      const body = JSON.parse(lastCall[1].body);
      
      expect(body.session_id).toBe("test-session-123");
    });
  });

  it("closes chat when X button is clicked", async () => {
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Open chat
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    await waitFor(() => {
      expect(screen.getByText("AI Food Assistant")).toBeInTheDocument();
    });
    
    // Click X button
    const closeButton = screen.getByRole("button", { name: "" }); // X icon button
    fireEvent.click(closeButton);
    
    // Should show launch button again
    await waitFor(() => {
      expect(screen.getByText("Let AI recommend me something")).toBeInTheDocument();
    });
  });

  it("handles API error gracefully", async () => {
    // Mock failed API response
    (fetch as any).mockRejectedValue(new Error("Network error"));
    
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Open chat
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    // Wait for error message
    await waitFor(() => {
      expect(screen.getByText(/Sorry, I'm having trouble connecting/i)).toBeInTheDocument();
    });
  });

  it("does not send message when input is empty", async () => {
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Open chat
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Tell me what you're craving/i)).toBeInTheDocument();
    });
    
    // Try to send empty message
    const input = screen.getByPlaceholderText(/Tell me what you're craving/i);
    fireEvent.keyDown(input, { key: "Enter" });
    
    // Should not call fetch
    expect(fetch).not.toHaveBeenCalled();
  });

  it("does not open chat when no token is available", () => {
    // Mock no token
    Storage.prototype.getItem = vi.fn(() => null);
    
    render(<AIChatWidget onAddToCart={mockOnAddToCart} />);
    
    // Try to open chat
    fireEvent.click(screen.getByText("Let AI recommend me something"));
    
    // Should not show chat content
    expect(screen.queryByText("AI Food Assistant")).not.toBeInTheDocument();
  });
});
