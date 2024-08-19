document.addEventListener('DOMContentLoaded', (event) => {
    document.getElementById('MainUserID').value = localStorage.getItem('selectedMainUserID') || 'all';
    document.getElementById('year').value = localStorage.getItem('selectedYear') || 'all';
    document.getElementById('month').value = localStorage.getItem('selectedMonth') || 'all';

    document.getElementById('MainUserID').onchange = function () {
        localStorage.setItem('selectedMainUserID', this.value);
    }
    document.getElementById('year').onchange = function () {
        localStorage.setItem('selectedYear', this.value);
    }
    document.getElementById('month').onchange = function () {
        localStorage.setItem('selectedMonth', this.value);
    }

    const images = document.querySelectorAll('.data-item img');
    const modal = document.createElement('div');
    modal.classList.add('modal');

    const modalImg = document.createElement('img');
    modalImg.classList.add('modal-content');
    modal.appendChild(modalImg);

    const closeBtn = document.createElement('span');
    closeBtn.classList.add('close');
    closeBtn.innerHTML = '&times;';
    modal.appendChild(closeBtn);

    document.body.appendChild(modal);

    images.forEach(image => {
        image.onclick = function () {
            modal.style.display = 'block';
            modalImg.src = this.src;
        }
    });

    closeBtn.onclick = function () {
        modal.style.display = 'none';
    }

    modal.onclick = function (e) {
        if (e.target !== modalImg) {
            modal.style.display = 'none';
        }
    }
});
