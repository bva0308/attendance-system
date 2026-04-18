setTimeout(() => {
  document.querySelectorAll(".flash").forEach((node) => {
    node.style.opacity = "0";
    node.style.transition = "opacity 0.4s ease";
  });
}, 3000);
