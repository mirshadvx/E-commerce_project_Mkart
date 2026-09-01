CHECKOUT_PAYMENT_METHODS = {'cod', 'razorpay', 'wallet'}

PENDING_RAZORPAY_CHECKOUT_SESSION_KEY = 'pending_razorpay_checkout'
CHECKOUT_ADDRESS_SESSION_KEY = 'checkout_address_form_data'

RAZORPAY_RETRY_WINDOW_MINUTES = 10

RAZORPAY_FAILURE_MESSAGES = {
    'payment_failed': 'Payment failed. Your order is pending and can be paid within 10 minutes.',
    'payment_cancelled': 'Payment was cancelled. Your order is pending and can be paid within 10 minutes.',
    'payment_dismissed': 'Payment window was closed. Your order is pending and can be paid within 10 minutes.',
    'payment_start_failed': 'Unable to start Razorpay payment. Please try again.',
    'verification_failed': "Payment verification failed. Please contact support if money was debited.",
    'session_mismatch': 'Payment session mismatch. Please refresh checkout and try again.',
    'payment_expired': 'Payment time expired. The order was cancelled and stock has been released.',
}

CHECKOUT_ADDRESS_FIELDS = (
    'selected_address',
    'use_new_address',
    'full_name',
    'last_name',
    'phone_number',
    'email',
    'address_line_1',
    'address_line_2',
    'city',
    'state',
    'postal_code',
    'country',
)
