document.addEventListener("DOMContentLoaded", function () {
    const menuIcon = document.getElementById("menubar");
    const navUL = document.querySelector("nav ul");

    // Add an event listener to the menu icon
    menuIcon.addEventListener("click", function () {
        // Toggle the visibility of the navigation menu
        if (navUL.style.display === "block") {
            navUL.style.display = "none";
        } else {
            navUL.style.display = "block";
        }
    });
});