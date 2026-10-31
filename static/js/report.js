document.addEventListener("DOMContentLoaded", function () {
    const ctx = document.getElementById("resultChart");
    if (!ctx) return;

    // Mock data for the chart. In a real app, this would come from the backend.
    const correctAnswers = 16;
    const wrongAnswers = 4;

    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Correct", "Wrong"],
            datasets: [{
                data: [correctAnswers, wrongAnswers],
                backgroundColor: ["#22c55e", "#ef4444"],
                borderColor: "rgba(255, 255, 255, 0.1)",
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
});