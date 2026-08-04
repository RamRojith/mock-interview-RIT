// Reference to the logout timer
let logoutTimer = null;
const logoutDelayInMinutes = 60; // Delay time in minutes
const logoutDelay = logoutDelayInMinutes * 60 * 1000; // Convert minutes to milliseconds

// Function to reset the logout timer
function resetLogoutTimer() {
    if (logoutTimer) {
        clearTimeout(logoutTimer); // Clear the current timer
    }

    // Set a new logout timer
    logoutTimer = setTimeout(() => {
        // Perform logout logic when the user is idle
        fetch('/logout', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url; // Redirect to login
            }
        })
        .catch(error => {
            console.error('Logout error:', error);
        });
    }, logoutDelay);
}

// Activity events for desktop and mobile
const activityEvents = [
    'mousemove', 'keydown', 'scroll', 'click', 
    'touchstart', 'touchmove', 'touchend', 
    'pointerdown', 'pointermove', 'pointerup' // Pointer events
];

// Attach event listeners to reset the timer on user activity
activityEvents.forEach(event => {
    window.addEventListener(event, (e) => {
        resetLogoutTimer(); // Reset the logout timer on any user interaction
    });
});

// Start the logout timer initially
resetLogoutTimer();



