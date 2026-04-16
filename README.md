# RestroManager 🍽️
*We are "vibe coding" our way to a better dining experience.*

## 🎯 Product Vision
**RestroManager** is a full-stack university project designed to act as the ultimate digital manager for modern restaurants. Our primary goal is to **smooth out the customer experience** by removing traditional dining friction—from waiting for menus to trying to catch a waiter's attention. By connecting the Customer, Waiter, Chef, and Manager into one seamless, real-time digital flow, RestroManager ensures faster service, fewer errors, and a more enjoyable environment for everyone.

---

## 👤 User Stories

### 📱 For the Customer
* **US 1:** As a customer, I want to view the digital menu by categories (drinks, main courses, desserts) with pictures and ingredients, so that I know exactly what I'm ordering and can find items quickly.
* **US 2:** As a customer, I want to add special instructions to a dish (e.g., "no onion" or "well done"), so that my food respects my dietary preferences and allergies.
* **US 3:** As a customer, I want to securely pay online with my card directly in the app, so that I can save time and leave whenever I'm ready without waiting for the physical bill.
* **US 4:** As a customer, I want a "Call Waiter" button in the app, so that I can easily request assistance or order extras without having to wave across the room.

### 🏃 For the Waiter
* **US 5:** As a waiter, I want to see a color-coded floor map showing the real-time status of each table (free, occupied, waiting for food, bill requested), so that I know exactly where my attention is needed.
* **US 6:** As a waiter, I want to receive a push notification on my device when an order is ready in the kitchen, so that I can serve the food hot and fresh immediately.
* **US 7:** As a waiter, I want to receive a push notification on my device when one of my customers calls me, so I can be there for them ASAP and assist them.
* **US 8:** As a waiter, I want to manually input orders into the system for customers not using the app, so that all restaurant orders stay synced in one central digital flow.

### 👨‍🍳 For the Chef
* **US 9:** As a chef, I want to see a Kitchen Display System (KDS) with order tickets ordered chronologically, so that I know exactly what to prioritize and cook first.
* **US 10:** As a chef, I want to mark a dish/order as "Ready to serve" with a single tap, so that it automatically notifies the assigned waiter to pick it up.

### 👔 For the Manager
* **US 11:** As a manager, I want to easily add, edit, or remove menu items and prices, so that I can keep the restaurant's offering updated in real-time without reprinting physical menus.
* **US 12:** As a manager, I want to generate an end-of-day sales report, so that I can track total revenue and identify the best-selling menu items.

---

## 🛠️ Tech Stack
To ensure a highly responsive, real-time experience while maintaining a clean and scalable codebase, RestroManager is built using a modern decoupled architecture:

* **Frontend:** Next.js (React), Tailwind CSS, shadcn/ui
* **Backend:** FastAPI (Python)
* **Database:** PostgreSQL via SQLModel
* **Real-time Communication:** WebSockets (Native FastAPI)
* **Payments:** Stripe Python SDK

---

## 📐 System Architecture

The system decouples the client-facing interfaces from the backend logic. Standard requests (like fetching the menu or processing payments) use REST API endpoints, while time-sensitive events (like calling a waiter or kitchen notifications) utilize WebSockets for instantaneous updates.

```mermaid
flowchart TB
    subgraph Frontend [Frontend - Next.js & Tailwind]
        direction LR
        C[📱 Customer App]
        W[🏃 Waiter App]
        K[👨‍🍳 Chef KDS]
        M[👔 Manager Dashboard]
    end

    subgraph Backend [Backend - FastAPI Python]
        API[⚙️ REST API Routes]
        WS[⚡ WebSocket Manager]
    end

    subgraph Database [Database]
        DB[(🐘 PostgreSQL via SQLModel)]
    end

    subgraph External [External Services]
        S[💳 Stripe API - Payments]
    end

    %% REST HTTP Relations (Solid lines)
    C -->|HTTP GET/POST| API
    W -->|HTTP GET/POST| API
    K -->|HTTP GET/POST| API
    M -->|HTTP GET/POST| API

    %% WebSockets Relations (Dotted lines for Real-time)
    C -.->|WebSockets| WS
    W -.->|WebSockets| WS
    K -.->|WebSockets| WS

    %% Internal Connections
    API <-->|Queries/Transactions| DB
    WS <-->|Status Notifications| DB
    API <-->|Generate Checkout Session| S
