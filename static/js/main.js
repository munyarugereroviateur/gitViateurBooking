document.addEventListener('DOMContentLoaded', function () {
  // Client-side validation for booking form
  const bookingForm = document.querySelector('#booking-form');
  if (bookingForm) {
    bookingForm.addEventListener('submit', function (e) {
      const seat = bookingForm.querySelector('[name="seat_number"]');
      if (!seat.value.match(/^[0-9]{1,2}[A-F]$/)) {
        e.preventDefault();
        alert('Seat number must look like 12A, 3F, etc.');
      }
    });
  }

  // AJAX: refresh delay probability for a flight via Fetch API
  document.querySelectorAll('.refresh-delay').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const flightId = btn.dataset.flightId;
      fetch(`/api/flights/${flightId}/delay_prediction/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      })
        .then((res) => res.json())
        .then((data) => {
          const badge = document.querySelector(`#delay-badge-${flightId}`);
          badge.textContent = data.delay_probability + '%';
        })
        .catch((err) => console.error('Delay fetch failed:', err));
    });
  });
});