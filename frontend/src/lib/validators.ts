/**
 * Client-side form validation utilities.
 * Each validator returns an error message string or null if valid.
 *
 * Requirements: 1.3, 1.5, 1.6
 */

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Validates an email address.
 * Must be non-empty and match a basic email format.
 * Requirement 1.5
 */
export function validateEmail(email: string): string | null {
  const trimmed = email.trim();
  if (!trimmed) {
    return "Email is required";
  }
  if (!EMAIL_REGEX.test(trimmed)) {
    return "Please enter a valid email address";
  }
  return null;
}

/**
 * Validates a password.
 * Must be 8-128 characters.
 * Requirement 1.3
 */
export function validatePassword(password: string): string | null {
  if (!password) {
    return "Password is required";
  }
  if (password.length < 8) {
    return "Password must be at least 8 characters";
  }
  if (password.length > 128) {
    return "Password must be no more than 128 characters";
  }
  return null;
}

/**
 * Validates a name field.
 * Must be 1-100 characters and not whitespace-only.
 * Requirement 1.6
 */
export function validateName(name: string): string | null {
  const trimmed = name.trim();
  if (!trimmed) {
    return "Name is required";
  }
  if (trimmed.length > 100) {
    return "Name must be no more than 100 characters";
  }
  return null;
}
