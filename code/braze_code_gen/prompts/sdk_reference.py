"""SDK Reference Examples for the Code Generation Agent.

This module contains trimmed, authoritative SDK code patterns extracted from
the Braze Web SDK Integration Guide. These serve as reference examples to
guide the code generation agent in producing correct SDK integrations.
"""

SDK_REFERENCE_EXAMPLES = """
**CRITICAL INSTRUCTION**: The base template already includes SDK initialization with the
ACTUAL API key and SDK endpoint from the user's Braze configuration. DO NOT copy the
placeholder patterns below (like 'BRAZE_API_KEY' or 'BRAZE_SDK_ENDPOINT') into your generated
code. Instead, PRESERVE the real API key and baseUrl values that are already configured
in the base template's braze.initialize() call.

These reference examples show correct METHOD SIGNATURES and USAGE PATTERNS only.
NEVER output placeholder strings - always use the actual configured values from the base template.

---

### SDK Async Loader Pattern (REFERENCE ONLY - base template already has initialization)
```javascript
+function(a,p,P,b,y){
    a.braze={};
    a.brazeQueue=[];
    // Creates stub methods that queue calls until SDK loads
    for(var s="BrazeSdkMetadata DeviceProperties Card ... [full method list]".split(" "),i=0;i<s.length;i++){
        for(var m=s[i],k=a.braze,l=m.split("."),j=0;j<l.length-1;j++)k=k[l[j]];
        k[l[j]]=(new Function("return function "+m.replace(/\\./g,"_")+"(){window.brazeQueue.push(arguments); return true}"))()
    }
    window.braze.getUser=function(){return new window.braze.User};
    (y=p.createElement(P)).type='text/javascript';
    y.src='https://js.appboycdn.com/web-sdk/6.5/braze.min.js';
    y.async=1;
    y.onload = function() {
        braze.initialize('BRAZE_API_KEY', {
            baseUrl: "BRAZE_SDK_ENDPOINT",
            allowUserSuppliedJavascript: true,
            minimumIntervalBetweenTriggerActionsInSeconds: 0,
            enableLogging: true
        });
        braze.openSession();
        braze.requestContentCardsRefresh();
        braze.subscribeToContentCardsUpdates(function(cards) {
            console.log("Content Cards Updated:", cards);
        });
    };
    (b=p.getElementsByTagName(P)[0]).parentNode.insertBefore(y,b);
}(window,document,'script');
```

### User Identification
```javascript
// Change the current user (call after login/signup)
braze.changeUser("user_id_123");

```

### Standard User Attributes
```javascript
const user = braze.getUser();

user.setFirstName("John");
user.setLastName("Doe");
user.setEmail("john.doe@example.com");
user.setGender(braze.User.Genders.MALE);  // MALE, FEMALE, OTHER, UNKNOWN, NOT_APPLICABLE, PREFER_NOT_TO_SAY
user.setDateOfBirth(1990, 5, 15);         // year, month (1-12), day
user.setCountry("United States");
user.setHomeCity("New York");
user.setPhoneNumber("+1234567890");
user.setLanguage("en");
```

### Custom User Attributes
```javascript
const user = braze.getUser();

// String attribute
user.setCustomUserAttribute("favorite_color", "blue");

// Number attribute
user.setCustomUserAttribute("loyalty_points", 500);

// Boolean attribute
user.setCustomUserAttribute("is_premium_member", true);

// Date attribute
user.setCustomUserAttribute("last_purchase_date", new Date());

// Array attribute
user.setCustomUserAttribute("favorite_genres", ["rock", "jazz", "classical"]);

// Add to array
user.addToCustomAttributeArray("favorite_genres", "blues");

// Remove from array
user.removeFromCustomAttributeArray("favorite_genres", "rock");

// Increment numeric attribute
user.incrementCustomUserAttribute("loyalty_points", 50);
```

### Custom Events
```javascript
// Log a simple event
braze.logCustomEvent("viewed_product");

// Log event with properties
braze.logCustomEvent("added_to_cart", {
    product_id: "SKU123",
    product_name: "Blue Widget",
    price: 29.99,
    quantity: 2,
    category: "widgets"
});

// Log event with nested properties
braze.logCustomEvent("completed_level", {
    level: 5,
    score: 1500,
    time_spent: 120,
    achievements: ["first_win", "speed_demon"]
});
```

### Purchase Tracking
```javascript
// Log a simple purchase
braze.logPurchase("product_sku", 29.99, "USD", 1);

// Log purchase with properties
braze.logPurchase("product_sku", 29.99, "USD", 2, {
    category: "electronics",
    brand: "Acme",
    coupon_code: "SAVE10",
    is_gift: false
});
```

### Content Cards
```javascript
// Show content cards in a container
const container = document.getElementById("content-cards-container");
braze.showContentCards(container);

// Hide content cards
braze.hideContentCards();

// Toggle content cards visibility
braze.toggleContentCards(container);

// Request a refresh of content cards
braze.requestContentCardsRefresh();

// Subscribe to content card updates
braze.subscribeToContentCardsUpdates(function(cards) {
    console.log("Received cards:", cards.cards);
    console.log("Unviewed count:", cards.getUnviewedCardCount());

    // Process cards manually if needed
    cards.cards.forEach(function(card) {
        console.log("Card ID:", card.id);
        console.log("Card Title:", card.title);

        // Log impression
        braze.logContentCardImpressions([card]);

        // Log click (call when user clicks)
        braze.logContentCardClick(card);
    });
});

// Dismiss a card
card.dismissCard();
```

### In-App Messages
```javascript
// Automatically show in-app messages (default behavior)
braze.automaticallyShowInAppMessages();

// Or manually handle in-app messages
braze.subscribeToInAppMessage(function(inAppMessage) {
    console.log("Received IAM:", inAppMessage);

    // Show it
    braze.showInAppMessage(inAppMessage);

    // Log impression
    braze.logInAppMessageImpression(inAppMessage);

    // Log click
    braze.logInAppMessageClick(inAppMessage);

    // For messages with buttons
    if (inAppMessage.buttons && inAppMessage.buttons.length > 0) {
        inAppMessage.buttons.forEach(function(button, index) {
            braze.logInAppMessageButtonClick(inAppMessage, button);
        });
    }

    // Close the message programmatically
    inAppMessage.closeMessage();
});

// Subscribe to click/dismiss events
inAppMessage.subscribeToClickedEvent(function() {
    console.log("Message was clicked");
});
inAppMessage.subscribeToDismissedEvent(function() {
    console.log("Message was dismissed");
});
```

### Push Notifications
```javascript
// Check if push is supported
if (braze.isPushSupported()) {
    console.log("Push is supported");
}

// Check if push permission is granted
braze.isPushPermissionGranted().then(function(isGranted) {
    console.log("Push permission granted:", isGranted);
});

// Request push permission (shows browser prompt)
braze.requestPushPermission(
    function() {
        console.log("Push permission granted!");
    },
    function() {
        console.log("Push permission denied");
    }
);

// Unregister from push
braze.unregisterPush();

// Set push notification subscription type
const user = braze.getUser();
user.setPushNotificationSubscriptionType(
    braze.User.NotificationSubscriptionTypes.OPTED_IN
    // Options: OPTED_IN, SUBSCRIBED, UNSUBSCRIBED
);
```

### Feature Flags
```javascript
// Refresh feature flags from server
braze.refreshFeatureFlags();

// Get all feature flags
const allFlags = braze.getAllFeatureFlags();

// Get a specific feature flag
const flag = braze.getFeatureFlag("my_feature_flag");

if (flag && flag.enabled) {
    // Feature is enabled, use its properties
    const stringProp = flag.getStringProperty("button_text");
    const numberProp = flag.getNumberProperty("max_items");
    const boolProp = flag.getBooleanProperty("show_banner");
    const imageProp = flag.getImageProperty("hero_image");
    const jsonProp = flag.getJsonProperty("config");
    const timestampProp = flag.getTimestampProperty("start_date");
}

// Log feature flag impression (for analytics)
braze.logFeatureFlagImpression("my_feature_flag");

// Subscribe to feature flag updates
braze.subscribeToFeatureFlagsUpdates(function(flags) {
    console.log("Feature flags updated:", flags);
});
```

### User Aliases & Subscription Groups
```javascript
const user = braze.getUser();

// Add an alias to the user
user.addAlias("my_alias", "alias_label");

// Add user to a subscription group
user.addToSubscriptionGroup("subscription_group_id");

// Remove user from a subscription group
user.removeFromSubscriptionGroup("subscription_group_id");

// Set email notification subscription type
user.setEmailNotificationSubscriptionType(
    braze.User.NotificationSubscriptionTypes.OPTED_IN
);

// Get the user ID (async)
user.getUserId(function(userId) {
    console.log("User ID:", userId);
});
```

### Data Management & Utilities
```javascript
// Force immediate data flush to Braze servers
braze.requestImmediateDataFlush();

// Get the device ID
braze.getDeviceId(function(deviceId) {
    console.log("Device ID:", deviceId);
});

// Enable/disable SDK
braze.disableSDK();
braze.enableSDK();

// Check if SDK is disabled/initialized
const isDisabled = braze.isDisabled();
const isInitialized = braze.isInitialized();

// Toggle console logging (useful for debugging)
braze.toggleLogging();

// Set a custom logger
braze.setLogger(function(message) {
    console.log("[Braze]", message);
});

// Wipe all user data (use with caution!)
braze.wipeData();

// Set SDK authentication signature
braze.setSdkAuthenticationSignature("your_jwt_token");

// Subscribe to SDK authentication failures
braze.subscribeToSdkAuthenticationFailures(function(event) {
    console.log("Auth failure:", event);
});
```
"""
