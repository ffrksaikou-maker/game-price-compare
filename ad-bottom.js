// AdSense: 全ページ共通の最下部枠。自動広告は使わず、この1枠だけ出す(見た目を崩さないため)
// トップ4ページはテンプレートに同じ枠(.adsense-bottom)を直接置いているので、その場合は何もしない
(function () {
  if (document.querySelector('.adsense-bottom')) return;
  var d = document.createElement('div');
  d.className = 'adsense-bottom';
  d.style.cssText = 'max-width:728px;margin:24px auto;padding:0 10px;clear:both';
  d.innerHTML = '<ins class="adsbygoogle" style="display:block" data-ad-client="ca-pub-5831186943118320" data-ad-slot="6504414651" data-ad-format="auto" data-full-width-responsive="true"></ins>';
  document.body.appendChild(d);
  (window.adsbygoogle = window.adsbygoogle || []).push({});
})();
