export enum BookingStatus {
    CONFIRMED = "CONFIRMED",
    TENTATIVE = "TENTATIVE",
    CANCELLED = "CANCELLED",
    PAID = "PAID",
}

export enum PaymentMethod {
    CASH = "CASH",
    TRANSFER = "TRANSFER",
    CARD = "CARD",
    OTHER = "OTHER",
}

export enum BookingSource {
    AIRBNB = "AIRBNB",
    BOOKING = "BOOKING",
    DIRECT = "DIRECT",
    MANUAL = "MANUAL",
}

export enum DocumentType {
    DU = "DU",
    EXTRANJERO = "EXTRANJERO",
}

export enum UserRole {
    ADMIN = "admin",
    MANAGER = "manager",
    OWNER = "owner",
}

export enum PricingAdjustmentType {
    PERCENTAGE = "PERCENTAGE",   // base price * (1 + value / 100)
    FIXED_PRICE = "FIXED_PRICE", // value replaces the nightly price
}

export interface PricingRule {
    id: string; // uuid
    property_id: string; // uuid
    name: string;
    start_date: string; // YYYY-MM-DD
    end_date: string; // YYYY-MM-DD
    adjustment_type: string | PricingAdjustmentType;
    adjustment_value: number; // > -100 for PERCENTAGE, > 0 for FIXED_PRICE
    priority: number;         // highest wins when rules overlap; tie -> most recent
    created_at?: string;
    updated_at?: string;
}

export interface CalendarDay {
    date: string; // YYYY-MM-DD
    price: number;
    status: "AVAILABLE" | "RESERVED";
    rule_name?: string | null;
}

export interface FinancialSummary {
    year: number;
    month: number;
    days_in_month: number;
    occupied_days: number;
    occupancy_rate: number;
    total_bookings: number;
    total_income: number;   // paid_income + pending_income
    paid_income: number;    // PAID bookings
    pending_income: number; // CONFIRMED / TENTATIVE bookings
}

export interface User {
    id: string; // uuid
    username: string;
    email: string;
    full_name: string;
    role: string | UserRole;
    is_active: boolean;
    created_at: string; // datetime
}

export interface Property {
    id: string; // uuid
    name: string;
    address: string;
    description?: string;
    manager_id: string; // uuid
    owner_id?: string; // uuid
    base_price: number; // Precio bruto por noche
    latitude?: number | null;
    longitude?: number | null;
    // Catalog (public catalog + chatbot); null on legacy properties
    max_guests?: number | null;
    amenities?: string[] | null;
    check_in_time?: string | null; // HH:MM:SS
    check_out_time?: string | null; // HH:MM:SS
    cancellation_policy?: string | null;
    house_rules?: string | null;
    created_at: string; // datetime
    updated_at: string; // datetime
    is_active: boolean;
}

export interface Guest {
    id: string; // uuid
    full_name: string;
    email: string;
    phone?: string;
    document_type: string | DocumentType;
    document_number: string;
    created_at: string; // datetime
}

export interface Booking {
    id: string; // uuid
    ical_uid?: string;
    property_id: string; // uuid
    guest_id: string; // uuid
    check_in: string; // date YYYY-MM-DD
    check_out: string; // date YYYY-MM-DD
    summary: string;
    description?: string;
    status: string | BookingStatus;
    source: string | BookingSource;
    total_amount?: number | null;  // Calculated at creation time
    paid_amount?: number | null;   // Actual amount received (set when paid)
    paid_at?: string | null; // date YYYY-MM-DD
    payment_method?: string | PaymentMethod | null;
    external_id?: string;
    ical_url?: string;
    last_synced_at?: string; // datetime
    created_at: string; // datetime
    updated_at: string; // datetime
}

export interface PriceQuote {
    total_amount: number;
    nights: number;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
}

export interface PropertyBasePrice {
    id: string; // uuid
    property_id: string; // uuid
    value: number;
    is_active: boolean;
    start_date?: string | null;   // YYYY-MM-DD, null = "from the beginning"
    end_date?: string | null;     // YYYY-MM-DD, null = currently active
    root_price_id?: string | null; // uuid, null = this is the root version
    created_at?: string;
    updated_at?: string;
}

export interface PropertyBasePriceModify {
    value: number;
    start_date: string; // YYYY-MM-DD
}
