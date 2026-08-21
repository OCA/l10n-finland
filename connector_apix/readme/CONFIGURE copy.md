## Creating EnableBanking application
1. Create an Application in https://enablebanking.com/cp/applications
 - Your redirect URL should be https://your-odoo.com/enablebanking_auth
 - Fill in email for data protection matters, Privacy URL and Terms URL
2. Save the Application ID and Private key (.pem -file) for the next step.
3. Link your accounts, unless you plan to request general availability

## Configuring Odoo
1. Enable "Show Full Accounting Features" group/permission to your user
2. Go to Invoicing->Configuration->EnableBanking Applications
3. Create a new application and provide the following information:
 - Application ID (from previous step)
 - Bank. It should have the correct BIC code
 - Responsible user for this application
 - Account type (Personal/Business)
 - Redirect URL. This needs to be allowed in the previous step
 - Company
 - Private key (the .pem-file you got from the previous step)
4. Click "Get ASPSP info" to fetch bank information from EnableBanking. If your credentials are correct, you should see bank name and ASPSP name filled in.
5. Click "Bank authentication" and follow instructions to complete the authentication

Basic configuration is now ready. You can proceed to authenticate and fetch bank statements.


## Authenticating to bank
1. Go to Invoicing->Configuration->Journals
2. Create (or edit) a journal belonging to a bank account
3. Fill the "Bank Account Number" with your IBAN number and a corresponding bank with BIC-number
3. Select "Online (OCA)" from Bank Feeds
4. Select "EnableBanking" for Provider
5. Click "Configuration"-button next to provider, and select the application you created in previous steps.
6. Configure transactions interval here: Day/Week/Month
7. If you want to fetch old transactions, click "Pull Online Bank Statement" and define the range for fetching

Done! A re-authentication will be required every 3-6 months (depending on the bank).
You can wait for the authentication to expire, or renew it while it's still active.