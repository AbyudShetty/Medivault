document.addEventListener("DOMContentLoaded", () => {
  // View prescription in modal (if you have this feature)
  const viewModal = document.getElementById("viewModal");
  const viewImg = document.getElementById("viewImg");
  document.querySelectorAll(".gallery-card").forEach(card => {
    card.addEventListener("click", () => {
      const imgSrc = card.getAttribute("data-img");
      if (imgSrc) {
        viewImg.src = imgSrc;
        const modal = new bootstrap.Modal(viewModal);
        modal.show();
      }
    });
  });
});

// DO NOT PUT ANY UPLOAD FORM CODE HERE!