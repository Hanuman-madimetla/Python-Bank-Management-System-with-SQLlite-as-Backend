import sqlite3
import hashlib
from getpass import getpass

# ---------------- Utility ----------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

import math


# ---------------- Input Validation ----------------

def get_username(prompt):
    while True:
        username = input(prompt).strip()

        if username == "":
            print("Username cannot be empty!")
        elif " " in username:
            print("Username cannot contain spaces!")
        else:
            return username


def get_password(prompt):
    while True:
        password = getpass(prompt)

        if password == "":
            print("Password cannot be empty!")
        elif len(password) < 4:
            print("Password must contain at least 4 characters!")
        else:
            return password


def get_amount(prompt):
    while True:
        try:
            amount = float(input(prompt))

            if not math.isfinite(amount):
                print("Please enter a valid finite number!")
            elif amount <= 0:
                print("Amount must be greater than zero!")
            else:
                return amount

        except ValueError:
            print("Invalid amount! Please enter a valid number.")

# ---------------- Database Setup ----------------
def setup_database():
    connection = sqlite3.connect("bank_management_system.db")
    connection.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        balance REAL NOT NULL CHECK(balance >= 0),
        status TEXT NOT NULL DEFAULT 'active'
    )
    """)
    connection.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        account_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL CHECK(amount > 0),
        details TEXT,
        timestamp TEXT DEFAULT (datetime('now','localtime')),
        FOREIGN KEY (account_id) REFERENCES accounts(id)
    )
    """)
    connection.commit()
    connection.close()

# ---------------- Registration ----------------
def register():
    connection = sqlite3.connect("bank_management_system.db")
    username = get_username("Choose a username: ")
    password = get_password("Choose a password: ")
    repeat_password = get_password("Repeat your password: ")

    if password == repeat_password:
        hashed_pw = hash_password(password)
        try:
            connection.execute("""
                INSERT INTO accounts (username, password, balance)
                VALUES (?, ?, ?)
            """, (username, hashed_pw, 5000))
            connection.commit()
            print("Account inserted successfully! Please login now.")
        except sqlite3.IntegrityError:
            print("Username already exists. Please choose another.")
    else:
        print("Passwords do not match. Please try again.")
    connection.close()

# ---------------- Login ----------------
def login():
    username_input = get_username("Enter your username: ")
    password_input = get_password("Enter your password: ")
    hashed_pw_input = hash_password(password_input)

    connection = sqlite3.connect("bank_management_system.db")
    cursor = connection.execute(
        "SELECT * FROM accounts WHERE username = ? AND password = ?",
        (username_input, hashed_pw_input)
    )
    row = cursor.fetchone()

    if row is None:
        print("Invalid username or password!")
        connection.close()
        return None, None, None
    else:
        print(f"Welcome {row[1]}! Your current balance is: ₹{row[3]:.2f}")
        return connection, row, username_input
# ---------------- Deposit ----------------
def deposit(connection, row, username_input):
    amount = get_amount("Enter the amount to deposit: ")

    new_balance = row[3] + amount

    try:
        connection.execute(
            "UPDATE accounts SET balance = ? WHERE username = ?",
            (new_balance, username_input)
        )

        connection.execute(
            "INSERT INTO transactions (account_id, type, amount, details) VALUES (?, ?, ?, ?)",
            (row[0], "Deposit", amount, "Deposited to own account")
        )

        connection.commit()

    except sqlite3.Error:
        connection.rollback()
        print("Deposit failed. Please try again.")

    else:
        row = (row[0], row[1], row[2], new_balance)
        print(f"Deposited ₹{amount}. New balance is: ₹{new_balance:.2f}")

    return row


# ---------------- Withdraw ----------------
def withdraw(connection, row, username_input):
    amount = get_amount("Enter the amount to withdraw: ")

    if amount > row[3]:
        print("Insufficient funds!")
        return row

    new_balance = row[3] - amount

    try:
        connection.execute(
            "UPDATE accounts SET balance = ? WHERE username = ?",
            (new_balance, username_input)
        )

        connection.execute(
            "INSERT INTO transactions (account_id, type, amount, details) VALUES (?, ?, ?, ?)",
            (row[0], "Withdrawal", amount, "Withdrawn from own account")
        )

        connection.commit()

    except sqlite3.Error:
        connection.rollback()
        print("Withdrawal failed. Please try again.")

    else:
        row = (row[0], row[1], row[2], new_balance)
        print(f"Withdrew ₹{amount}. New balance is: ₹{new_balance:.2f}")

    return row


# ---------------- Transfer ----------------
def transfer(connection, row, username_input):
    recipient_username = get_username("Enter the recipient's username: ")

    if recipient_username == username_input:
        print("You cannot transfer money to yourself!")
        return row

    amount = get_amount("Enter the amount to transfer: ")

    if amount > row[3]:
        print("Insufficient funds!")
        return row

    cursor = connection.execute(
        "SELECT * FROM accounts WHERE username = ?",
        (recipient_username,)
    )

    recipient_row = cursor.fetchone()

    if recipient_row is None:
        print("Recipient account does not exist!")
        return row

    new_balance_sender = row[3] - amount
    new_balance_recipient = recipient_row[3] + amount

    try:
        # Update sender
        connection.execute(
            "UPDATE accounts SET balance = ? WHERE username = ?",
            (new_balance_sender, username_input)
        )

        # Update recipient
        connection.execute(
            "UPDATE accounts SET balance = ? WHERE username = ?",
            (new_balance_recipient, recipient_username)
        )

        # Record transaction for sender
        connection.execute(
            "INSERT INTO transactions (account_id, type, amount, details) VALUES (?, ?, ?, ?)",
            (row[0], "Transfer", amount, f"→ {recipient_username}")
        )

        # Record transaction for recipient
        connection.execute(
            "INSERT INTO transactions (account_id, type, amount, details) VALUES (?, ?, ?, ?)",
            (recipient_row[0], "Transfer Received", amount, f"← {username_input}")
        )

        connection.commit()

    except sqlite3.Error:
        connection.rollback()
        print("Transaction failed. Please try again.")

    else:
        row = (row[0], row[1], row[2], new_balance_sender)
        print(
            f"Transferred ₹{amount} to {recipient_username}. "
            f"New balance is: ₹{new_balance_sender:.2f}"
        )

    return row
# ---------------- Transaction History ----------------
def transaction_history(connection, row):
    cursor = connection.execute("""
        SELECT timestamp, type, amount, details
        FROM transactions
        WHERE account_id = ?
        ORDER BY timestamp DESC
    """, (row[0],))
    transactions = cursor.fetchall()

    if not transactions:
        print("No transactions found.")
    else:
        print("\nDate                  Type               Amount       Details")
        print("---------------------------------------------------------------")
        for t in transactions:
            print(f"{t[0]:<20} {t[1]:<18} ₹{t[2]:<10} {t[3]}")

# ---------------- Account Details ----------------
def account_details(row):
    print("\n--- Account Details ---")
    print(f"Account ID : {row[0]}")
    print(f"Username   : {row[1]}")
    print(f"Balance    : ₹{row[3]:.2f}")

# ---------------- Change Password ----------------
def change_password(connection, row, username_input):
    current_pw = get_password("Enter your current password: ")
    if hash_password(current_pw) != row[2]:
        print("Incorrect current password!")
    else:
        new_pw = get_password("Enter new password: ")
        repeat_pw = get_password("Repeat new password: ")
        if new_pw != repeat_pw:
            print("Passwords do not match!")
        else:
            new_hashed_pw = hash_password(new_pw)
            connection.execute(
                "UPDATE accounts SET password = ? WHERE username = ?",
                (new_hashed_pw, username_input)
            )
            connection.commit()
            print("Password changed successfully!")
# -------------change username----------------
def change_username(connection, row, username_input):
    new_username = get_username("Enter new username: ")
    if new_username == username_input:
        print("New username cannot be the same as the current username!")
    else:
        try:
            connection.execute(
                "UPDATE accounts SET username = ? WHERE username = ?",
                (new_username, username_input)
            )
            connection.commit()
            print(f"Username changed successfully to {new_username}!")
            return new_username  # Return the new username for further operations
        except sqlite3.IntegrityError:
            print("Username already exists. Please choose another.")
    return username_input  # Return the original username if change failed
# ------- Deactivate Account ----------------
def deactivate_account(connection, row, username_input):

    confirmation = input(
        "Are you sure you want to deactivate your account? (yes/no): "
    ).strip().lower()

    if confirmation != "yes":
        print("Account deactivation canceled.")
        return False

    # If money is still present
    if row[3] > 0:

        print(f"Your current balance is: ₹{row[3]:.2f}")

        withdraw_confirmation = input(
            "Would you like to withdraw your remaining balance? (yes/no): "
        ).strip().lower()

        if withdraw_confirmation != "yes":
            print("Account deactivation canceled. Please withdraw your balance first.")
            return False

        remaining_balance = row[3]

        try:
            # Withdraw remaining balance
            connection.execute(
                "UPDATE accounts SET balance = ? WHERE username = ?",
                (0, username_input)
            )

            # Record the withdrawal
            connection.execute(
                """
                INSERT INTO transactions
                (account_id, type, amount, details)
                VALUES (?, ?, ?, ?)
                """,
                (
                    row[0],
                    "Withdrawal",
                    remaining_balance,
                    "Final withdrawal before account deactivation"
                )
            )

            connection.commit()

            print(
                f"₹{remaining_balance:.2f} withdrawn successfully."
            )

            # Update current row
            row = (row[0], row[1], row[2], 0)

        except sqlite3.Error:
            connection.rollback()
            print("Failed to withdraw your balance. Account was not deactivated.")
            return False

    # At this point balance is definitely 0
    try:
        connection.execute(
            "DELETE FROM accounts WHERE username = ?",
            (username_input,)
        )

        connection.execute(
            "DELETE FROM transactions WHERE account_id = ?",
            (row[0],)
        )

        connection.commit()

        print("Account deactivated successfully. Goodbye!")
        return True

    except sqlite3.Error:
        connection.rollback()
        print("Failed to deactivate account. Please try again.")
        return False
# ----------------- profile settings----------------
def profile_settings(connection, row, username_input):
    while True:
        print("\n========== PROFILE SETTINGS ==========")
        print("1. Account Details")
        print("2. Change Password")
        print("3. Change Username")
        print("4. Deactivate Account")
        print("5. Back to Service Menu")

        choice = input("Enter your choice (1-5): ")

        if choice == "1":
            account_details(row)

        elif choice == "2":
            change_password(connection, row, username_input)

        elif choice == "3":
            username_input = change_username(connection, row, username_input)

        elif choice == "4":
            if deactivate_account(connection, row, username_input): 
              return True 
    
        elif choice == "5":
            break  # Exit profile settings

        else:
            print("Invalid choice! Please select a valid option.")
    return False  # Return False if account was not deactivated
# ---------------- Service Menu ----------------
def service_menu(connection, row, username_input):

    while True:
        print("\n========== SERVICE MENU ==========")
        print("1. Deposit")
        print("2. Withdraw")
        print("3. Transfer")
        print("4. Transaction History")
        print("5. Account Details")
        print("6. Profile Settings")
        print("7. Logout")

        choice = input("Enter your choice (1-7): ")

        if choice == "1":
            row = deposit(connection, row, username_input)

        elif choice == "2":
            row = withdraw(connection, row, username_input)

        elif choice == "3":
            row = transfer(connection, row, username_input)

        elif choice == "4":
            transaction_history(connection, row)

        elif choice == "5":
            account_details(row)

        elif choice == "6":
           account_deactivated = profile_settings(
           connection, row, username_input 
           )
         
           if account_deactivated:
                  return

        elif choice == "7":
            print("You have been logged out.")
            break

        

        else:
            print("Invalid choice! Please select a valid option.")


# ---------------- Main Function ----------------
def main():

    setup_database()

    print("\n========== WELCOME TO OUR BANK ==========")

    while True:

        print("\n1. Login")
        print("2. Register")
        print("3. Exit")

        choice = input("Enter your choice (1-3): ")

        if choice == "1":

            result = login()

            if result[0] is not None:
                connection, row, username_input = result

                service_menu(connection, row, username_input)

                connection.close()

        elif choice == "2":

            register()

        elif choice == "3":

            print("Thank you for using our bank!")
            break

        else:
            print("Invalid choice! Please select 1, 2, or 3.")


# ---------------- Program Start ----------------
if __name__ == "__main__":
    main()
